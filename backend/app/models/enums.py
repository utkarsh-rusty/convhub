import enum


class WorkspaceRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AIRequestStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversationParticipantRole(str, enum.Enum):
    OWNER = "owner"
    MEMBER = "member"


class CreditTransactionType(str, enum.Enum):
    ALLOCATION = "allocation"
    USAGE = "usage"
    BORROW = "borrow"
    LEND = "lend"
    ADJUSTMENT = "adjustment"


class RoutingPolicyType(str, enum.Enum):
    OWNER_FIRST = "owner_first"
    BALANCED = "balanced"
    LOWEST_USAGE = "lowest_usage"
    CHEAPEST = "cheapest"
    PRIORITY = "priority"


class BorrowStrategyType(str, enum.Enum):
    HIGHEST_REMAINING = "highest_remaining"
