from app.ai.providers.anthropic import AnthropicProvider
from app.ai.providers.base import AIProvider
from app.ai.providers.mock import MockProvider
from app.core.config import Settings


def create_provider(
    provider_name: str,
    model: str,
    credentials: dict[str, str] | None,
    settings: Settings,
    *,
    allow_dev_fallback: bool = True,
) -> AIProvider:
    if provider_name == "mock":
        return MockProvider()

    if provider_name == "anthropic":
        api_key = credentials.get("api_key") if credentials else None
        if not api_key and allow_dev_fallback and settings.app_env == "development":
            api_key = settings.anthropic_api_key

        if not api_key:
            raise ValueError("No Anthropic credentials configured for this workspace")

        return AnthropicProvider(api_key=api_key, model=model)

    raise ValueError(f"Unsupported AI provider: {provider_name}")
