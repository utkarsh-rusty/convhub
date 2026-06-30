from decimal import Decimal, ROUND_CEILING

from app.ai.prompt_builder import PromptContext
from app.demo.context import get_active_pricing_profile
from app.resource_management.pricing_engine import PricingEngine

ESTIMATED_MAX_OUTPUT_TOKENS = 1024


class CreditPolicy:
    """Pricing policy — converts token usage into credit cost."""

    def __init__(self, pricing_engine: PricingEngine | None = None) -> None:
        self.pricing_engine = pricing_engine or PricingEngine()

    def calculate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> Decimal:
        profile = get_active_pricing_profile()
        multiplier = self.pricing_engine.multiplier_for(profile, provider)
        total_tokens = Decimal(max(0, input_tokens) + max(0, output_tokens))
        raw = (total_tokens / Decimal("1000")) * multiplier
        # TODO: apply per-model rates and workspace pricing plans.
        _ = model
        return raw.quantize(Decimal("0.01"), rounding=ROUND_CEILING)

    def estimate_request_cost(
        self,
        provider: str,
        model: str,
        prompt_context: PromptContext,
    ) -> Decimal:
        """Conservative pre-flight estimate used before calling a provider."""
        input_chars = len(prompt_context.system_prompt) + sum(
            len(message.content) for message in prompt_context.chat_messages
        )
        estimated_input_tokens = max(1, input_chars // 4)
        return self.calculate_cost(
            provider,
            model,
            estimated_input_tokens,
            ESTIMATED_MAX_OUTPUT_TOKENS,
        )
