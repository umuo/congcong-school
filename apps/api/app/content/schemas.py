from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

ContentKind = Literal["lesson", "challenge", "story", "number_review", "reading"]
QuestionType = Literal[
    "true_false",
    "choice",
    "fill_blank",
    "calculation",
    "word_problem",
    "fill_blank_text",
    "word_order",
    "matching",
]


class StrictSource(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CountVisual(StrictSource):
    kind: Literal["count"]
    count: int = Field(ge=0, le=1000)
    emoji: str
    label: str
    layout: Literal["line", "scatter", "frame"]


class CompareVisual(StrictSource):
    kind: Literal["compare"]
    left: int = Field(ge=0, le=1000)
    right: int = Field(ge=0, le=1000)
    leftEmoji: str
    rightEmoji: str
    leftLabel: str
    rightLabel: str


class ShareVisual(StrictSource):
    kind: Literal["share"]
    learners: int = Field(ge=0, le=1000)
    resources: int = Field(ge=0, le=1000)
    learnerEmoji: str
    resourceEmoji: str
    learnerLabel: str
    resourceLabel: str


class NumberTask(StrictSource):
    stage: Literal["guided", "independent", "transfer"]
    visual: CountVisual | CompareVisual | ShareVisual
    hints: list[str] = Field(min_length=2, max_length=2)


class QuestionAudio(StrictSource):
    question: str | None = None
    options: list[str | None] | None = None
    explanation: str | None = None


class PrivateQuestion(StrictSource):
    id: Annotated[StrictInt, Field(gt=0)]
    type: QuestionType
    score: int = Field(default=5, ge=0, le=1000)
    difficulty: int = Field(default=1, ge=1, le=5)
    knowledge_point: str = ""
    question: str = Field(min_length=1, max_length=20000)
    options: list[str] = Field(default_factory=list, max_length=26)
    answer: str = Field(min_length=1, max_length=20000)
    explanation: str = Field(default="", max_length=40000)
    audio: QuestionAudio | None = None
    numberTask: NumberTask | None = None
    skill: str | None = None
    evidence_sentence_indices: list[Annotated[int, Field(gt=0)]] | None = None


class QuestionRef(BaseModel):
    uid: str
    version: str
    source_question_id: int


class ContentView(BaseModel):
    id: str
    kind: ContentKind
    book_id: str
    source_id: str
    version: str
    metadata: dict
    question_refs: list[QuestionRef]


def public_question(payload: dict, *, uid: str, version: str) -> dict:
    keys = {
        "id",
        "type",
        "score",
        "difficulty",
        "knowledge_point",
        "question",
        "options",
        "numberTask",
    }
    public = {key: value for key, value in payload.items() if key in keys}
    if payload.get("numberTask"):
        public["numberTask"] = {
            key: value for key, value in payload["numberTask"].items() if key in {"stage", "visual"}
        }
    audio = payload.get("audio") or {}
    public_audio = {key: audio[key] for key in ["question", "options"] if key in audio}
    if public_audio:
        public["audio"] = public_audio
    return {**public, "uid": uid, "version": version}
