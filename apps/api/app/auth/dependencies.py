import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.adapters import TokenDatabase, strategy, user_manager
from app.auth.models import AuthSession, StudentAccount, User
from app.errors import APIError

SESSION_COOKIE = "csf_session"
CSRF_COOKIE = "csf_csrf"


async def session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.database.sessions() as value:
        yield value


def same_origin(request: Request) -> None:
    if request.headers.get("origin") != request.app.state.settings.public_origin:
        raise APIError(403, "ORIGIN_REJECTED", "请求来源未获授权")


@dataclass
class Identity:
    user: User
    auth_session: AuthSession


async def authenticated(
    request: Request, db: Annotated[AsyncSession, Depends(session)]
) -> Identity:
    token = request.cookies.get(SESSION_COOKIE)
    settings = request.app.state.settings
    user = await strategy(db, settings.session_lifetime_seconds).read_token(token, user_manager(db))
    if user is None or not user.is_active:
        raise APIError(401, "AUTH_REQUIRED", "请重新登录")
    row = await TokenDatabase(db).get_by_token(token)
    if row is None or row.principal_role != user.role:
        raise APIError(401, "AUTH_REQUIRED", "请重新登录")
    if user.role == "student":
        binding = await db.get(StudentAccount, user.id)
        if (
            binding is None
            or binding.student_id != row.student_id
            or binding.family_id != row.family_id
        ):
            raise APIError(401, "AUTH_REQUIRED", "请重新登录")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        same_origin(request)
        supplied = request.headers.get("x-csf-csrf", "")
        if not supplied or not secrets.compare_digest(
            TokenDatabase.digest(supplied), row.csrf_hash
        ):
            raise APIError(403, "CSRF_REJECTED", "请刷新页面后重试")
        # 与管理员停用/重置串行，避免已通过检查的写请求在撤销后继续提交。
        user = await db.scalar(
            select(User)
            .where(User.id == user.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            user is None
            or not user.is_active
            or await TokenDatabase(db).get_by_token(token) is None
        ):
            raise APIError(401, "AUTH_REQUIRED", "请重新登录")
    return Identity(user, row)


async def identity(who: Annotated[Identity, Depends(authenticated)]) -> Identity:
    if who.user.must_change_password:
        raise APIError(403, "PASSWORD_CHANGE_REQUIRED", "请先修改初始密码")
    return who


async def parent(who: Annotated[Identity, Depends(identity)]) -> Identity:
    if who.user.role != "parent" or who.auth_session.mode != "parent":
        raise APIError(403, "PARENT_REQUIRED", "请使用家长账号验证身份")
    return who


def recently_verified(request: Request, who: Identity) -> None:
    age = (datetime.now(UTC) - who.auth_session.parent_verified_at).total_seconds()
    if age > request.app.state.settings.parent_verification_seconds:
        raise APIError(403, "PARENT_REAUTH_REQUIRED", "请再次验证账号密码")


async def verified_parent(request: Request, who: Annotated[Identity, Depends(parent)]) -> Identity:
    recently_verified(request, who)
    return who


async def administrator(request: Request, who: Annotated[Identity, Depends(identity)]) -> Identity:
    if who.user.role != "admin" or who.auth_session.mode != "admin":
        raise APIError(403, "ADMIN_REQUIRED", "需要管理员权限")
    recently_verified(request, who)
    return who
