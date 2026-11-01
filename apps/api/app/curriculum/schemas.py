from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SubjectView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    name: str


class TextbookView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    subject_code: str
    title: str
    grade: int
    school_stage: str
    school_system: str
    semester: str
    publisher_label: str | None
    publisher: str | None
    edition_label: str | None
    source_edition: str | None
    source_printing: str | None
    publication_year: int | None
    isbn: str | None
    supersedes: str | None
    superseded_by: str | None
    units: list[dict]
    provenance: dict
    content_revision: str


class TextbookList(BaseModel):
    items: list[TextbookView]
    recommendations: list[str] = []
    recommendation_reason: str = "NO_VERIFIED_REGIONAL_DATA"


class SubjectChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    enabled: bool
    book_id: str | None = Field(default=None, max_length=120, pattern=r"^[a-z0-9-]+$")
    current_unit_number: int | None = Field(default=None, ge=1)


class CurriculumUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subjects: list[SubjectChoice] = Field(max_length=50)

    @model_validator(mode="after")
    def unique_subjects(self):
        ids = [s.subject_code for s in self.subjects]
        if len(ids) != len(set(ids)):
            raise ValueError("同一学科不能重复配置")
        return self


class SelectionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    subject_code: str
    book_id: str
    current_unit_number: int | None
    started_at: datetime
    ended_at: datetime | None
    snapshot: dict


class CurriculumView(BaseModel):
    revision: int
    subjects: list[SubjectChoice]
    history: list[SelectionView]
