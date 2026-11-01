from typing import Literal
from uuid import UUID

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def normalize_login(value: str) -> str:
    value = value.strip().casefold()
    if not 3 <= len(value) <= 320 or not all(c.isalnum() or c in "._@+-" for c in value):
        raise ValueError("账号须为 3–320 个字母、数字或 . _ @ + -，不能有空格")
    return value


class Login(StrictModel):
    login: str = Field(
        validation_alias=AliasChoices("login", "email"), min_length=3, max_length=320
    )
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("login")
    @classmethod
    def valid_login(cls, value):
        return normalize_login(value)


class ProfileUpdate(StrictModel):
    nickname: str = Field(min_length=1, max_length=80)

    @field_validator("nickname")
    @classmethod
    def clean_nickname(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("昵称不能为空")
        return value.strip()


class UserView(BaseModel):
    id: UUID
    login_name: str
    email: EmailStr | None
    nickname: str
    role: Literal["admin", "parent", "student"]


class FamilyView(BaseModel):
    id: UUID
    name: str
    timezone: str
    role: Literal["owner", "guardian"]


class AccountView(BaseModel):
    context_id: UUID
    user: UserView | None = None
    role: Literal["admin", "parent", "student"]
    family: FamilyView | None = None
    mode: Literal["admin", "parent", "child"]
    student_id: UUID | None = None
    must_change_password: bool
    destination: str


class PasswordVerification(StrictModel):
    password: SecretStr = Field(min_length=1, max_length=128)


class PasswordChange(PasswordVerification):
    new_password: SecretStr = Field(min_length=12, max_length=128)


class ChildSelection(StrictModel):
    student_id: UUID


class ChildModeView(BaseModel):
    mode: Literal["child"]
    student_id: UUID


class ChildProfileView(BaseModel):
    id: UUID
    nickname: str
    avatar: str
    grade: int
