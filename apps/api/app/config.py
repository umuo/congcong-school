from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

API_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CSF_", env_file=API_ROOT / ".env", extra="ignore")

    environment: str = "development"
    database_url: SecretStr
    content_root: Path = API_ROOT.parent.parent
    public_origin: str = "http://localhost:3000"
    cookie_secure: bool = True
    bootstrap_admin_login: str | None = None
    bootstrap_admin_password: SecretStr | None = None
    session_lifetime_seconds: int = Field(default=604800, ge=60)
    parent_verification_seconds: int = Field(default=300, ge=1)
    auth_rate_limit: int = Field(default=10, ge=1)
    auth_rate_window_seconds: int = Field(default=300, ge=1)
    backup_retention_days: int = Field(default=0, ge=0, le=365)
    deletion_journal: Path = API_ROOT / "private-content/deletions.jsonl"

    @field_validator("database_url")
    @classmethod
    def require_postgres(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
            if url.drivername != "postgresql+psycopg":
                raise ValueError
        except Exception:
            raise ValueError("CSF_DATABASE_URL 必须使用 postgresql+psycopg") from None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
