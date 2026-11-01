import hashlib
from datetime import UTC, datetime
from uuid import UUID

from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users.authentication.strategy.db import DatabaseStrategy
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import AuthSession, StudentAccount, User


class TransactionalUserDatabase(SQLAlchemyUserDatabase):
    """保留库的查询与验证能力，让注册用户和家庭在同一业务事务提交。"""

    async def create(self, create_dict):
        user = User(**create_dict)
        self.session.add(user)
        await self.session.flush()
        return user

    async def update(self, user, update_dict):
        for key, value in update_dict.items():
            setattr(user, key, value)
        await self.session.flush()
        return user


class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    async def authenticate(self, credentials):
        # 库默认按必填邮箱查找；仅替换身份查找，保留其密码校验/升级语义。
        user = await self.user_db.session.scalar(
            select(User)
            .where(User.login_name == credentials.username.strip().casefold())
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if user is None:
            self.password_helper.hash(credentials.password)
            return None
        valid, upgraded = self.password_helper.verify_and_update(
            credentials.password, user.hashed_password
        )
        if not valid:
            return None
        if upgraded:
            await self.user_db.update(user, {"hashed_password": upgraded})
        return user


class TokenDatabase:
    """复用 DatabaseStrategy 的随机令牌与到期语义，数据库只保存令牌摘要。"""

    def __init__(self, session: AsyncSession, csrf_hash: str = ""):
        self.session = session
        self.csrf_hash = csrf_hash

    @staticmethod
    def digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    async def get_by_token(self, token, max_age=None):
        statement = select(AuthSession).where(AuthSession.token == self.digest(token))
        if max_age is not None:
            statement = statement.where(AuthSession.created_at >= max_age)
        return await self.session.scalar(statement)

    async def create(self, create_dict):
        raw = create_dict["token"]
        now = datetime.now(UTC)
        user = await self.session.get(User, create_dict["user_id"])
        binding = (
            await self.session.get(StudentAccount, user.id) if user.role == "student" else None
        )
        row = AuthSession(
            token=self.digest(raw),
            user_id=create_dict["user_id"],
            created_at=now,
            parent_verified_at=now,
            csrf_hash=self.csrf_hash,
            mode="child" if user.role == "student" else user.role,
            principal_role=user.role,
            student_id=binding.student_id if binding else None,
            family_id=binding.family_id if binding else None,
        )
        self.session.add(row)
        await self.session.flush()
        # 库返回给浏览器的是原始令牌，持久化实体仍只有摘要。
        from types import SimpleNamespace

        return SimpleNamespace(token=raw)

    async def delete(self, row):
        await self.session.delete(row)
        await self.session.flush()


def user_manager(session: AsyncSession) -> UserManager:
    return UserManager(TransactionalUserDatabase(session, User))


def strategy(session: AsyncSession, lifetime: int, csrf_hash: str = ""):
    return DatabaseStrategy(TokenDatabase(session, csrf_hash), lifetime_seconds=lifetime)
