"""显式运行 python -m app.auth.bootstrap；不在 API 启动时隐式建号。"""

import asyncio

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.auth.models import User
from app.auth.schemas import normalize_login
from app.auth.service import create_account
from app.config import Settings, get_settings
from app.database import Database
from app.errors import APIError


async def bootstrap(settings: Settings, database: Database | None = None) -> bool:
    if not settings.bootstrap_admin_login or not settings.bootstrap_admin_password:
        raise ValueError("请配置 CSF_BOOTSTRAP_ADMIN_LOGIN 和 CSF_BOOTSTRAP_ADMIN_PASSWORD")
    login_name = normalize_login(settings.bootstrap_admin_login)
    password = settings.bootstrap_admin_password.get_secret_value()
    if not 12 <= len(password) <= 128:
        raise ValueError("初始密码须为 12–128 字符")
    own_database = database is None
    database = database or Database(settings)
    try:
        async with database.sessions() as db:
            # 事务锁让多个初始化进程串行，已有管理员永不覆盖。
            await db.execute(text("SELECT pg_advisory_xact_lock(306637001)"))
            if await db.scalar(select(User.id).where(User.role == "admin")):
                return False
            if await db.scalar(select(User.id).where(User.login_name == login_name)):
                raise ValueError("初始账号与既有普通账号重名，不能提升其权限")
            await create_account(
                db, login_name=login_name, password=password, nickname="管理员", role="admin"
            )
            await db.commit()
            return True
    except IntegrityError:
        raise ValueError("管理员初始化冲突，未创建账号") from None
    finally:
        if own_database:
            await database.engine.dispose()


if __name__ == "__main__":
    try:
        created = asyncio.run(bootstrap(get_settings()))
        print("管理员已初始化，首次登录需修改密码" if created else "管理员已存在，未修改账号或密码")
    except (ValueError, APIError) as exc:
        raise SystemExit(str(exc)) from None
