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


class RepositoryProvider(str, enum.Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    OTHER = "other"


class RepositoryVisibility(str, enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    INTERNAL = "internal"


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


class ExecutionType(str, enum.Enum):
    OWN_PROVIDER = "own_provider"
    BORROWED_PROVIDER = "borrowed_provider"
    LOCAL_MODEL = "local_model"


class PricingProfileType(str, enum.Enum):
    PRODUCTION = "production"
    DEMO = "demo"
    FREE = "free"


class ProviderSimulationMode(str, enum.Enum):
    NORMAL = "normal"
    TIMEOUT = "timeout"
    UNAUTHORIZED = "unauthorized"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"


class RoutingOverrideMode(str, enum.Enum):
    NORMAL = "normal"
    FIRST_ACCOUNT = "first_account"
    SECOND_ACCOUNT = "second_account"
    RANDOM = "random"
    SPECIFIC_ACCOUNT = "specific_account"
