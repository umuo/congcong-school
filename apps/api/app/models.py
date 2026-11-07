"""集中登记模型，供 Alembic 元数据比较使用。"""

from app.auth.models import AuthRateLimit, AuthSession, StudentAccount, User
from app.content.models import ContentContainer, ContentRevision, QuestionIdentity, QuestionVersion
from app.curriculum.models import StudentSubject, Subject, Textbook, TextbookSelection
from app.diagnostics.models import (
    KnowledgePoint,
    KnowledgePointRelation,
    QuestionKnowledgeLink,
)
from app.families.models import Family, Membership
from app.learning.models import (
    Attempt,
    EconomyState,
    LearningCursor,
    LearningEvent,
    LearningReceipt,
    LearningSession,
    RewardClaim,
    RewardLedger,
)
from app.portability.models import DeletionReceipt, LegacyImport
from app.students.models import Student

__all__ = [
    "DeletionReceipt",
    "LegacyImport",
    "Attempt",
    "EconomyState",
    "RewardLedger",
    "RewardClaim",
    "LearningCursor",
    "LearningEvent",
    "LearningReceipt",
    "LearningSession",
    "ContentContainer",
    "ContentRevision",
    "QuestionIdentity",
    "QuestionVersion",
    "AuthRateLimit",
    "AuthSession",
    "Family",
    "Membership",
    "Student",
    "StudentAccount",
    "User",
    "StudentSubject",
    "Subject",
    "Textbook",
    "TextbookSelection",
    "KnowledgePoint",
    "KnowledgePointRelation",
    "QuestionKnowledgeLink",
]
