import hashlib
import secrets
import time
from uuid import NAMESPACE_URL, uuid5

from fastapi import Request, Response
from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.adapters import TokenDatabase, strategy, user_manager
from app.auth.dependencies import CSRF_COOKIE, SESSION_COOKIE
from app.auth.models import AuthRateLimit, AuthSession, StudentAccount, User
from app.errors import APIError
from app.families.models import Family, Membership


async def throttle(db: AsyncSession, request: Request, email: str, action: str) -> None:
    settings = request.app.state.settings
    window = int(time.time()) // settings.auth_rate_window_seconds
    ip = request.client.host if request.client else "unknown"
    counts = []
    for scope, limit in [
        (f"{action}:{ip}:{email.casefold()}", settings.auth_rate_limit),
        (f"{action}:{ip}", settings.auth_rate_limit * 5),
    ]:
        key = hashlib.sha256(scope.encode()).hexdigest()
        statement = insert(AuthRateLimit).values(key=key, window=window, attempts=1)
        statement = statement.on_conflict_do_update(
            index_elements=[AuthRateLimit.key],
            set_={
                "window": window,
                "attempts": case(
                    (AuthRateLimit.window == window, AuthRateLimit.attempts + 1), else_=1
                ),
            },
        ).returning(AuthRateLimit.attempts)
        counts.append((await db.scalar(statement), limit))
    await db.execute(delete(AuthRateLimit).where(AuthRateLimit.window < window - 1))
    # 失败请求也必须计入限流；先持久化次数，再进行账号事务。
    await db.commit()
    if any(count > limit for count, limit in counts):
        raise APIError(429, "AUTH_RATE_LIMITED", "尝试次数过多，请稍后重试")


async def create_account(
    db: AsyncSession,
    *,
    login_name: str,
    password: str,
    nickname: str,
    role: str,
    email: str | None = None,
    must_change_password: bool | None = None,
) -> User:
    user = User(
        login_name=login_name,
        email=email.casefold() if email else None,
        hashed_password=user_manager(db).password_helper.hash(password),
        nickname=nickname,
        role=role,
        must_change_password=(role == "admin")
        if must_change_password is None
        else must_change_password,
    )
    db.add(user)
    await db.flush()
    return user


async def revoke_sessions(db: AsyncSession, user_id) -> None:
    await db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))


async def sign_in(
    db: AsyncSession, request: Request, response: Response, user: User
) -> AuthSession:
    settings = request.app.state.settings
    csrf = secrets.token_urlsafe(32)
    # 新登录撤销当前浏览器携带的旧会话，避免跨账号遗留有效会话。
    old = request.cookies.get(SESSION_COOKIE)
    if old:
        row = await TokenDatabase(db).get_by_token(old)
        if row:
            await TokenDatabase(db).delete(row)
    token = await strategy(
        db, settings.session_lifetime_seconds, TokenDatabase.digest(csrf)
    ).write_token(user)
    await db.commit()
    for name, value, http_only in [(SESSION_COOKIE, token, True), (CSRF_COOKIE, csrf, False)]:
        response.set_cookie(
            name,
            value,
            httponly=http_only,
            secure=settings.cookie_secure,
            samesite="lax",
            path="/",
            max_age=settings.session_lifetime_seconds,
        )
    return await TokenDatabase(db).get_by_token(token)


def user_view(user: User) -> dict:
    return {
        "id": str(user.id),
        "login_name": user.login_name,
        "email": user.email,
        "nickname": user.nickname,
        "role": user.role,
    }


async def family_view(db: AsyncSession, user: User) -> dict:
    result = await db.execute(
        select(Family, Membership.role)
        .join(Membership, Membership.family_id == Family.id)
        .where(Membership.user_id == user.id)
    )
    row = result.first()
    if not row:
        raise APIError(404, "FAMILY_NOT_FOUND", "找不到家庭")
    family, role = row
    return {"id": str(family.id), "name": family.name, "timezone": family.timezone, "role": role}


def client_context(user: User, auth_session: AuthSession):
    return uuid5(
        NAMESPACE_URL,
        f"csf-client-scope-1:{auth_session.token}:{user.id}:{auth_session.mode}:{auth_session.student_id}:{auth_session.family_id}",
    )


async def account_view(db: AsyncSession, user: User, auth_session: AuthSession) -> dict:
    mode = auth_session.mode if auth_session else ("child" if user.role == "student" else user.role)
    student_id = auth_session.student_id if auth_session else None
    if user.role == "student":
        binding = await db.get(StudentAccount, user.id)
        student_id = binding.student_id if binding else None
    destination = (
        "/change-password"
        if user.must_change_password
        else {"admin": "/admin", "parent": "/parent", "child": "/learn"}[mode]
    )
    return {
        # 非凭据的缓存上下文标识；不公开会话令牌、摘要或家长身份。
        "context_id": client_context(user, auth_session),
        "user": user_view(user) if mode != "child" else None,
        "role": user.role,
        "mode": mode,
        "student_id": student_id,
        "must_change_password": user.must_change_password,
        "destination": destination,
        "family": await family_view(db, user)
        if user.role == "parent" and mode == "parent" and not user.must_change_password
        else None,
    }
