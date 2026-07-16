from enum import Enum


class ReviewStatus(str, Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_REVIEW = "IN_REVIEW"
    FIXED = "FIXED"
    APPROVED = "APPROVED"
    IGNORED_WITH_REASON = "IGNORED_WITH_REASON"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"
