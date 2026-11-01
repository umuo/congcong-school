from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.adapters import strategy, user_manager
from app.auth.dependencies import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    Identity,
    authenticated,
    identity,
    parent,
    same_origin,
    session,
    verified_parent,
)
from app.auth.models import StudentAccount
from app.auth.schemas import (
    AccountView,
    ChildModeView,
    ChildProfileView,
    ChildSelection,
    FamilyView,
    Login,
    PasswordChange,
    PasswordVerification,
    ProfileUpdate,
    UserView,
)
from app.errors import APIError
from app.students.models import Student
from app.students.service import authorized_student

router = APIRouter(prefix="/api/v1")
DB = Annotated[AsyncSession, Depends(session)]
Auth = Annotated[Identity, Depends(identity)]


@router.post("/auth/register", include_in_schema=False)
async def closed_registration():
    raise APIError(403, "REGISTRATION_CLOSED", "账号由管理员创建，请联系管理员")


async def authenticate(db: AsyncSession, login_name: str, password: str):
    user = await user_manager(db).authenticate(
        OAuth2PasswordRequestForm(username=login_name, password=password)
    )
    if user is None or not user.is_active:
        raise APIError(401, "INVALID_CREDENTIALS", "账号或密码不正确")
    if user.role == "student":
        student = await db.scalar(
            select(Student)
            .join(
                StudentAccount,
                (StudentAccount.student_id == Student.id)
                & (StudentAccount.family_id == Student.family_id),
            )
            .where(StudentAccount.user_id == user.id, Student.archived_at.is_(None))
        )
        if student is None:
            raise APIError(401, "INVALID_CREDENTIALS", "账号或密码不正确")
    return user


@router.post("/auth/login", response_model=AccountView, dependencies=[Depends(same_origin)])
async def login(body: Login, request: Request, response: Response, db: DB):
    await service.throttle(db, request, body.login, "login")
    user = await authenticate(db, body.login, body.password.get_secret_value())
    auth_session = await service.sign_in(db, request, response, user)
    return await service.account_view(db, user, auth_session)


@router.post("/auth/logout", status_code=204)
async def logout(
    request: Request, response: Response, who: Annotated[Identity, Depends(authenticated)], db: DB
):
    await strategy(db, request.app.state.settings.session_lifetime_seconds).destroy_token(
        request.cookies[SESSION_COOKIE], who.user
    )
    await db.commit()
    for name in [SESSION_COOKIE, CSRF_COOKIE]:
        response.delete_cookie(name, path="/", secure=request.app.state.settings.cookie_secure)


@router.get("/auth/session", response_model=AccountView)
async def current_session(who: Annotated[Identity, Depends(authenticated)], db: DB):
    if who.user.role == "student":
        await authorized_student(db, who, who.auth_session.student_id, for_learning=True)
    return await service.account_view(db, who.user, who.auth_session)


@router.post("/auth/change-password", response_model=AccountView)
async def change_password(
    body: PasswordChange,
    request: Request,
    response: Response,
    who: Annotated[Identity, Depends(authenticated)],
    db: DB,
):
    await service.throttle(db, request, who.user.login_name, "change-password")
    user = await authenticate(db, who.user.login_name, body.password.get_secret_value())
    if body.password.get_secret_value() == body.new_password.get_secret_value():
        raise APIError(422, "PASSWORD_UNCHANGED", "新密码不能与原密码相同")
    user.hashed_password = user_manager(db).password_helper.hash(
        body.new_password.get_secret_value()
    )
    user.must_change_password = False
    await service.revoke_sessions(db, user.id)
    auth_session = await service.sign_in(db, request, response, user)
    return await service.account_view(db, user, auth_session)


@router.get("/me", response_model=UserView)
async def me(who: Annotated[Identity, Depends(parent)]):
    return service.user_view(who.user)


@router.patch("/me", response_model=UserView)
async def update_me(
    body: ProfileUpdate, who: Annotated[Identity, Depends(verified_parent)], db: DB
):
    who.user.nickname = body.nickname
    await db.commit()
    return service.user_view(who.user)


@router.get("/family", response_model=FamilyView)
async def family(who: Annotated[Identity, Depends(parent)], db: DB):
    return await service.family_view(db, who.user)


@router.post("/mode/child", response_model=ChildModeView)
async def child_mode(
    body: ChildSelection, who: Annotated[Identity, Depends(verified_parent)], db: DB
):
    student = await authorized_student(db, who, body.student_id, for_learning=True)
    who.auth_session.mode = "child"
    who.auth_session.student_id = student.id
    who.auth_session.family_id = student.family_id
    await db.commit()
    return {"mode": "child", "student_id": student.id}


async def verify_parent(
    body: PasswordVerification,
    request: Request,
    response: Response,
    who: Identity,
    db: AsyncSession,
):
    if who.user.role != "parent":
        raise APIError(403, "PARENT_REQUIRED", "请退出后使用家长账号登录")
    await service.throttle(db, request, who.user.login_name, "reauth")
    user = await authenticate(db, who.user.login_name, body.password.get_secret_value())
    await service.family_view(db, user)
    auth_session = await service.sign_in(db, request, response, user)
    return await service.account_view(db, user, auth_session)


@router.post("/mode/parent", response_model=AccountView)
async def parent_mode(
    body: PasswordVerification, request: Request, response: Response, who: Auth, db: DB
):
    return await verify_parent(body, request, response, who, db)


@router.post("/auth/reauth", response_model=AccountView)
async def reauth(
    body: PasswordVerification, request: Request, response: Response, who: Auth, db: DB
):
    if who.user.role == "student":
        raise APIError(403, "PARENT_REQUIRED", "请退出后使用家长账号登录")
    if who.user.role == "parent":
        return await verify_parent(body, request, response, who, db)
    await service.throttle(db, request, who.user.login_name, "reauth")
    user = await authenticate(db, who.user.login_name, body.password.get_secret_value())
    auth_session = await service.sign_in(db, request, response, user)
    return await service.account_view(db, user, auth_session)


@router.get("/learning/profile", response_model=ChildProfileView)
async def learning_profile(who: Auth, db: DB):
    if who.auth_session.mode != "child":
        raise APIError(403, "CHILD_MODE_REQUIRED", "请先选择孩子学习档案")
    student = await authorized_student(db, who, who.auth_session.student_id, for_learning=True)
    return {
        "id": student.id,
        "nickname": student.nickname,
        "avatar": student.avatar,
        "grade": student.grade,
    }
