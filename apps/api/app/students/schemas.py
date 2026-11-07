from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.avatars.catalog import DEFAULT_AVATAR, AvatarID


class StudentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nickname: str = Field(min_length=1, max_length=80)
    avatar: AvatarID = DEFAULT_AVATAR
    birth_month: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    province: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=80)
    school: str | None = Field(default=None, max_length=120)
    school_stage: Literal["primary", "junior", "senior"] = "primary"
    grade: int = Field(default=1, ge=1, le=12)
    school_year: str | None = Field(default=None, pattern=r"^\d{4}-\d{4}$")
    semester: Literal["up", "down"] = "up"
    daily_goal_minutes: int = Field(default=20, ge=1, le=240)
    parent_notes: str | None = Field(default=None, max_length=2000)

    @field_validator("nickname")
    @classmethod
    def clean_nickname(cls, value):
        if not value.strip():
            raise ValueError("昵称不能为空")
        return value.strip()

    @field_validator("birth_month")
    @classmethod
    def valid_birth_month(cls, value):
        if value and (value[:4] == "0000" or value > date.today().strftime("%Y-%m")):
            raise ValueError("出生年月无效")
        return value

    @field_validator("school_year")
    @classmethod
    def valid_school_year(cls, value):
        if value and int(value[5:]) != int(value[:4]) + 1:
            raise ValueError("学年应为连续两年")
        return value


class StudentView(StudentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    archived_at: datetime | None
    revision: int


class StudentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nickname: str | None = Field(default=None, min_length=1, max_length=80)
    avatar: AvatarID | None = None
    birth_month: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    province: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=80)
    school: str | None = Field(default=None, max_length=120)
    school_stage: Literal["primary", "junior", "senior"] | None = None
    grade: int | None = Field(default=None, ge=1, le=12)
    school_year: str | None = Field(default=None, pattern=r"^\d{4}-\d{4}$")
    semester: Literal["up", "down"] | None = None
    daily_goal_minutes: int | None = Field(default=None, ge=1, le=240)
    parent_notes: str | None = Field(default=None, max_length=2000)

    @field_validator("nickname")
    @classmethod
    def clean_nickname(cls, value):
        return StudentCreate.clean_nickname(value) if value is not None else value

    @field_validator("birth_month")
    @classmethod
    def valid_birth_month(cls, value):
        return StudentCreate.valid_birth_month(value)

    @field_validator("school_year")
    @classmethod
    def valid_school_year(cls, value):
        return StudentCreate.valid_school_year(value)

    @model_validator(mode="after")
    def required_values_cannot_be_cleared(self):
        for key in {
            "nickname",
            "avatar",
            "school_stage",
            "grade",
            "semester",
            "daily_goal_minutes",
        }:
            if key in self.model_fields_set and getattr(self, key) is None:
                raise ValueError(f"{key} 不能清空")
        return self
