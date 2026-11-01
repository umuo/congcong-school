from uuid import UUID

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator

from app.auth.schemas import ProfileUpdate, StrictModel, normalize_login
from app.students.schemas import StudentCreate


class Credentials(ProfileUpdate):
    login_name: str = Field(min_length=3, max_length=320)
    password: SecretStr = Field(min_length=12, max_length=128)
    email: EmailStr | None = None

    @field_validator("login_name")
    @classmethod
    def valid_login(cls, value):
        return normalize_login(value)


class ParentCreate(Credentials):
    family_id: UUID | None = None
    family_name: str | None = Field(default=None, min_length=1, max_length=80)

    @model_validator(mode="after")
    def explicit_family(self):
        if (self.family_id is None) == (self.family_name is None):
            raise ValueError("选择已有家庭或填写新家庭名称")
        if self.family_name is not None and not self.family_name.strip():
            raise ValueError("家庭名称不能为空")
        return self


class StudentAccountCreate(Credentials):
    family_id: UUID
    student_id: UUID | None = None
    profile: StudentCreate | None = None

    @model_validator(mode="after")
    def explicit_student(self):
        if (self.student_id is None) == (self.profile is None):
            raise ValueError("选择已有学生或填写新档案")
        return self


class ResetPassword(StrictModel):
    password: SecretStr = Field(min_length=12, max_length=128)
