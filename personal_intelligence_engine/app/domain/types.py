"""Domain types and enumerations for PIE."""

from enum import Enum


class EntryType(str, Enum):
    """Taxonomy of structured entry types."""

    LOG = "log"
    IDEA = "idea"
    INSIGHT = "insight"
    CANDIDATE_TASK = "candidate_task"
    REFERENCE = "reference"
    DECISION = "decision"
    PROBLEM = "problem"
    REVIEW = "review"
    GENERAL_NOTE = "general_note"


class EntryStatus(str, Enum):
    """Status of a raw entry through the pipeline."""

    PENDING = "pending"
    PROCESSED = "processed"
    NEEDS_REVIEW = "needs_review"
    ERROR = "error"


class ValidationStatus(str, Enum):
    """Validation result of a structured entry."""

    VALID = "valid"
    NEEDS_REVIEW = "needs_review"
    INVALID = "invalid"


class AuditAction(str, Enum):
    """Actions tracked in the audit log."""

    ENTRY_CREATED = "entry_created"
    EXTRACTION_COMPLETED = "extraction_completed"
    VALIDATION_COMPLETED = "validation_completed"
    STRUCTURED_ENTRY_CREATED = "structured_entry_created"
    MARKDOWN_GENERATED = "markdown_generated"
    REPORT_GENERATED = "report_generated"
    LOW_CONFIDENCE = "low_confidence"
    VALIDATION_FAILED = "validation_failed"


class AuditStatus(str, Enum):
    """Status of an audit log event."""

    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


# Threshold below which confidence triggers needs_review
LOW_CONFIDENCE_THRESHOLD = 0.70
