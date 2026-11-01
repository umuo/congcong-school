import asyncio
import os
import subprocess
from pathlib import Path

import httpx
import psycopg
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from app.config import Settings
from app.main import create_app

API_ROOT = Path(__file__).resolve().parents[1]


def migrate(url: str, *args: str) -> None:
    env = {**os.environ, "CSF_DATABASE_URL": url}
    result = subprocess.run(
        [str(API_ROOT / ".venv/bin/alembic"), *args],
        cwd=API_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stderr


def test_settings_require_postgres():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="sqlite:///fallback.db")


@pytest.mark.asyncio
async def test_liveness_does_not_require_database():
    app = create_app(
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://test:test@127.0.0.1:1/unavailable",
        )
    )
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            live = await client.get("/health/live")
            ready = await client.get("/health/ready")
    assert live.json() == {"status": "ok"}
    assert ready.status_code == 503
    assert ready.json()["code"] == "DATABASE_NOT_READY"
    assert ready.json()["request_id"] == ready.headers["X-Request-ID"]
    assert live.headers["X-Request-ID"] != ready.headers["X-Request-ID"]
    assert "unavailable" not in ready.text


def test_empty_database_migration_round_trip(postgres_url):
    async def readiness():
        app = create_app(Settings(_env_file=None, database_url=postgres_url))
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await client.get("/health/ready")

    assert asyncio.run(readiness()).status_code == 503
    dsn = make_url(postgres_url).set(drivername="postgresql").render_as_string(hide_password=False)
    migrate(postgres_url, "upgrade", "head")
    with psycopg.connect(dsn) as connection:
        expected = ScriptDirectory.from_config(Config(API_ROOT / "alembic.ini")).get_current_head()
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            expected,
        )
        assert connection.execute("SELECT count(*) FROM families").fetchone() == (0,)
    assert asyncio.run(readiness()).status_code == 200
    migrate(postgres_url, "check")
    migrate(postgres_url, "downgrade", "base")
    with psycopg.connect(dsn) as connection:
        assert connection.execute("SELECT to_regclass('public.families')").fetchone() == (None,)
    assert asyncio.run(readiness()).status_code == 503
    migrate(postgres_url, "upgrade", "head")
    assert asyncio.run(readiness()).status_code == 200
