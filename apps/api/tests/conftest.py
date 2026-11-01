import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from psycopg import sql
from sqlalchemy.engine import make_url


@pytest.fixture
def postgres_url() -> Iterator[str]:
    """只创建并删除本测试生成的数据库；绝不清空传入的管理数据库。"""
    admin_url = os.environ.get("CSF_TEST_ADMIN_DATABASE_URL")
    if not admin_url:
        pytest.skip("Set CSF_TEST_ADMIN_DATABASE_URL for real PostgreSQL integration tests")
    url = make_url(admin_url)
    if url.drivername != "postgresql+psycopg":
        pytest.fail("Integration tests require PostgreSQL via psycopg")
    name = "cstf_test_" + uuid.uuid4().hex
    dsn = url.set(drivername="postgresql").render_as_string(hide_password=False)
    with psycopg.connect(dsn, autocommit=True, connect_timeout=10) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        yield url.set(database=name).render_as_string(hide_password=False)
    finally:
        with psycopg.connect(dsn, autocommit=True, connect_timeout=10) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


@pytest.fixture
async def auth_app(postgres_url):
    from app.config import Settings
    from app.main import create_app
    from tests.test_auth import ORIGIN
    from tests.test_foundation import migrate

    migrate(postgres_url, "upgrade", "head")
    app = create_app(Settings(_env_file=None, database_url=postgres_url, public_origin=ORIGIN))
    async with app.router.lifespan_context(app):
        yield app
