from datetime import UTC
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.content.schemas import CompareVisual, CountVisual, QuestionType, ShareVisual


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StartSession(StrictBody):
    kind: Literal["lesson", "challenge", "jump", "story", "number_review", "review", "reading"]
    book_id: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{0,119}$")
    source_id: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{0,159}$")
    target_unit: int | None = Field(default=None, ge=2, le=1000)
    number_skill: Literal["count", "compare", "apply"] | None = None
    client_at: AwareDatetime
    for_hearts: bool = False
    reading_kind: Literal["listen", "followup"] | None = None

    @model_validator(mode="after")
    def exact_source(self):
        if self.for_hearts and self.kind != "review":
            raise ValueError("仅复习支持回心补练")
        if (self.kind == "reading") != (self.reading_kind is not None):
            raise ValueError("听读活动必须指定 listen 或 followup")
        if self.kind in {"lesson", "challenge", "story", "reading"}:
            valid = (
                self.book_id and self.source_id and not self.target_unit and not self.number_skill
            )
        elif self.kind == "jump":
            valid = (
                self.book_id and self.target_unit and not self.source_id and not self.number_skill
            )
        elif self.kind == "number_review":
            valid = (
                self.number_skill
                and not self.source_id
                and not self.target_unit
                and not self.book_id
            )
        else:
            valid = not self.source_id and not self.target_unit and not self.number_skill
        if not valid:
            raise ValueError("请求来源字段与学习类型不一致")
        return self


class RevisionBody(StrictBody):
    revision: int = Field(ge=1)
    client_at: AwareDatetime


class AnswerBody(RevisionBody):
    question_uid: str = Field(pattern=r"^[a-f0-9]{64}$")
    question_version: str = Field(pattern=r"^[a-f0-9]{64}$")
    answer: str = Field(min_length=1, max_length=10000)
    declared_duration_ms: int = Field(default=0, ge=0, le=3600000)
    hint_level: int = Field(default=0, ge=0, le=2)
    evidence_sentence_indices: list[int] = Field(default_factory=list, max_length=100)


class DraftBody(RevisionBody):
    answer: str = Field(default="", max_length=10000)
    intro_page: int = Field(default=0, ge=0, le=100)
    visual_draft: list[int] = Field(default_factory=list, max_length=1000)
    evidence_sentence_indices: list[int] = Field(default_factory=list, max_length=100)


class MatchingPairBody(RevisionBody):
    question_uid: str = Field(pattern=r"^[a-f0-9]{64}$")
    question_version: str = Field(pattern=r"^[a-f0-9]{64}$")
    left: Literal["A", "B", "C", "D"]
    right: Literal["1", "2", "3", "4"]


class InputKeyboard(StrictBody):
    candidates: list[str]
    language: Literal["letters", "text"]
    max_length: int


class PublicAudio(StrictBody):
    question: str | None = None
    options: list[str | None] | None = None


class PublicNumberTask(StrictBody):
    stage: Literal["guided", "independent", "transfer"]
    visual: CountVisual | CompareVisual | ShareVisual
    hints: list[str] = Field(default_factory=list)
    hint_count: int = Field(default=0, ge=0)


class PublicQuestion(StrictBody):
    uid: str
    version: str
    id: int
    type: QuestionType
    question: str
    options: list[str]
    score: int
    difficulty: int
    knowledge_point: str
    audio: PublicAudio | None = None
    numberTask: PublicNumberTask | None = None
    input_keyboard: InputKeyboard | None = None


class AnswerFeedback(StrictBody):
    attempt_id: UUID
    correct: bool
    first_attempt: bool
    answer: str
    explanation: str
    explanation_audio: str | None
    evidence_sentence_indices: list[int]
    grading_rule_version: str
    submitted_answer: str | None = None
    submitted_evidence_indices: list[int] = Field(default_factory=list)


class SessionView(BaseModel):
    id: UUID
    student_id: UUID
    kind: str
    book_id: str | None
    source_id: str | None
    status: str
    revision: int
    cursor: int
    sources: list[dict]
    checkpoint: dict
    question: PublicQuestion | None
    feedback: AnswerFeedback | None
    settlement: dict | None = None


class MatchingPairView(BaseModel):
    correct: bool
    session: SessionView


class EconomyAction(StrictBody):
    kind: Literal[
        "league",
        "daily_reward",
        "quest",
        "chest",
        "buy_hearts",
        "buy_freeze",
        "makeup",
        "purchase_cosmetic",
        "equip_cosmetic",
        "set_daily_goal",
    ]
    client_at: AwareDatetime
    item_id: str | None = Field(default=None, max_length=100)
    quest_id: str | None = Field(default=None, max_length=100)
    chest_id: str | None = Field(default=None, max_length=200)
    book_id: str | None = Field(default=None, max_length=120)
    daily_goal: int | None = Field(default=None, ge=10, le=500)
    revision: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def associated_fields(self):
        fields = {
            name
            for name in ["item_id", "quest_id", "chest_id", "book_id", "daily_goal", "revision"]
            if getattr(self, name) is not None
        }
        expected = {
            "quest": {"quest_id"},
            "chest": {"chest_id", "book_id"},
            "purchase_cosmetic": {"item_id"},
            "equip_cosmetic": {"item_id"},
            "set_daily_goal": {"daily_goal", "revision"},
        }.get(self.kind, set())
        if fields != expected:
            raise ValueError("操作字段不匹配")
        return self


class CompleteBody(RevisionBody):
    abandon: bool = False


class TimeCheckpoint(StrictBody):
    kind: Literal["time_checkpoint"]
    session_id: UUID
    activity_id: UUID
    sequence: int = Field(ge=1, le=1_000_000_000)
    client_at: AwareDatetime
    started_at: AwareDatetime
    ended_at: AwareDatetime

    @model_validator(mode="after")
    def valid_interval(self):
        duration = (self.ended_at.astimezone(UTC) - self.started_at.astimezone(UTC)).total_seconds()
        if not 0 < duration <= 1800:
            raise ValueError("每个时间检查点必须在 0 至 30 分钟之间")
        return self
