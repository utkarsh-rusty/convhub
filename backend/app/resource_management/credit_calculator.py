from decimal import Decimal

from app.models.ai_request import AIRequest
from app.resource_management.credit_policy import CreditPolicy

_default_policy = CreditPolicy()


def calculate_credits(ai_request: AIRequest, policy: CreditPolicy | None = None) -> Decimal:
    """Convert a completed AIRequest into billable credits via CreditPolicy."""
    credit_policy = policy or _default_policy
    return credit_policy.calculate_cost(
        provider=ai_request.provider,
        model=ai_request.model,
        input_tokens=ai_request.input_tokens or 0,
        output_tokens=ai_request.output_tokens or 0,
    )
