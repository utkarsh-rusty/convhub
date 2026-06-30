from __future__ import annotations

from decimal import Decimal

from app.models.enums import PricingProfileType

PRODUCTION_MULTIPLIERS: dict[str, Decimal] = {
    "ollama": Decimal("0.00"),
    "mock": Decimal("0.00"),
    "anthropic": Decimal("1.0"),
    "openai": Decimal("1.0"),
    "gemini": Decimal("1.0"),
}

DEMO_MULTIPLIER = Decimal("1.0")
FREE_MULTIPLIER = Decimal("0.00")
DEFAULT_MULTIPLIER = Decimal("1.0")


class PricingEngine:
    """Single source of provider credit multipliers."""

    def multiplier_for(self, profile: PricingProfileType, provider: str) -> Decimal:
        provider_key = provider.lower()

        if profile == PricingProfileType.FREE:
            return FREE_MULTIPLIER

        if profile == PricingProfileType.DEMO:
            return DEMO_MULTIPLIER

        return PRODUCTION_MULTIPLIERS.get(provider_key, DEFAULT_MULTIPLIER)
