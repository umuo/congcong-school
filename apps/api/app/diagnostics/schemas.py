"""知识点目录与学生掌握度诊断响应契约。"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

DiagnosticStatus = Literal[
    "mastered",
    "developing",
    "needs_review",
    "insufficient_evidence",
    "unassessed",
]


class RelatedKnowledgeRef(BaseModel):
    kp_id: str
    book_id: str
    lesson_id: str | None = None
    title: str
    relation_kind: str
    status: DiagnosticStatus | None = None
    status_label: str | None = None


class KnowledgePointCatalogItem(BaseModel):
    id: str
    code: str
    scope_kind: str
    unit_number: int
    unit_title: str
    lesson_id: str | None = None
    title: str
    description: str | None = None
    sort_order: int
    total_questions_available: int
    related_points: list[RelatedKnowledgeRef] = []


class KnowledgeCatalogUnit(BaseModel):
    unit_number: int
    unit_title: str
    knowledge_points: list[KnowledgePointCatalogItem]


class TextbookKnowledgeCatalogView(BaseModel):
    book_id: str
    subject_code: str
    title: str
    grade: int
    semester: str
    school_system: str
    edition_label: str | None = None
    publisher_label: str | None = None
    mapping_version: str
    total_knowledge_points: int
    units: list[KnowledgeCatalogUnit]


class DiagnosticBookOption(BaseModel):
    book_id: str
    subject_code: str
    subject_name: str
    title: str
    grade: int
    semester: str
    school_system: str
    edition_label: str | None = None
    publisher_label: str | None = None
    is_current: bool
    current_unit_number: int | None = None


class DiagnosticSubjectOption(BaseModel):
    subject_code: str
    subject_name: str
    enabled: bool
    active_book_id: str | None = None


class KnowledgePointDiagnosticItem(BaseModel):
    id: str
    code: str
    scope_kind: str
    unit_number: int
    unit_title: str
    lesson_id: str | None = None
    title: str
    description: str | None = None
    sort_order: int
    status: DiagnosticStatus
    status_label: str
    diagnostic_rule_version: str
    reason_code: str
    reason_text: str
    total_questions_available: int
    distinct_questions_attempted: int
    distinct_sessions: int
    distinct_days: int
    total_attempts: int
    first_attempts_total: int
    first_attempts_correct: int
    unassisted_first_correct: int
    hint_assisted_count: int
    retry_attempts_total: int
    retry_attempts_correct: int
    first_accuracy: float | None = None
    unassisted_first_accuracy: float | None = None
    last_practiced_at: str | None = None
    last_study_day: str | None = None
    related_points: list[RelatedKnowledgeRef] = []


class DiagnosticUnitGroup(BaseModel):
    unit_number: int
    unit_title: str
    counts: dict[str, int]
    knowledge_points: list[KnowledgePointDiagnosticItem]


class DiagnosticSummaryCounts(BaseModel):
    total_knowledge_points: int
    assessed_count: int
    mastered_count: int
    developing_count: int
    needs_review_count: int
    insufficient_evidence_count: int
    unassessed_count: int
    total_attempts: int
    legacy_imports_count: int
    legacy_exclusion_note: str


class StudentDiagnosticsView(BaseModel):
    student_id: UUID
    timezone: str
    diagnostic_rule_version: str
    mapping_version: str
    selected_subject_code: str | None = None
    selected_book: DiagnosticBookOption | None = None
    subjects: list[DiagnosticSubjectOption]
    available_books: list[DiagnosticBookOption]
    summary: DiagnosticSummaryCounts
    priority_review: list[KnowledgePointDiagnosticItem]
    units: list[DiagnosticUnitGroup]


class AttemptEvidenceItem(BaseModel):
    attempt_id: str
    session_id: str
    session_kind: str
    question_uid: str
    question_version: str
    question_type: str
    question_stem: str
    correct: bool
    first_attempt: bool
    hint_level: int
    study_day: str
    received_at: str
    declared_duration_ms: int


class KnowledgePointDetailView(BaseModel):
    student_id: UUID
    timezone: str
    diagnostic_rule_version: str
    mapping_version: str
    book_id: str
    subject_code: str
    knowledge_point: KnowledgePointDiagnosticItem
    recent_attempts: list[AttemptEvidenceItem]
