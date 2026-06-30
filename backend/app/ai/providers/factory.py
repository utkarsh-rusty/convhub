from app.ai.providers.anthropic import AnthropicProvider
from app.ai.providers.base import AIProvider
from app.ai.providers.mock import MockProvider
from app.ai.providers.ollama import OllamaProvider
from app.core.config import Settings
from app.demo.context import get_demo_runtime
from app.demo.runtime import SimulatedFailureProvider
from app.models.enums import ProviderSimulationMode


def create_provider(
    provider_name: str,
    credentials: dict[str, str] | None,
    settings: Settings,
    *,
    allow_dev_fallback: bool = True,
) -> AIProvider:
    provider = _create_base_provider(
        provider_name,
        credentials,
        settings,
        allow_dev_fallback=allow_dev_fallback,
    )
    runtime = get_demo_runtime()
    if runtime is not None and runtime.provider_simulation != ProviderSimulationMode.NORMAL:
        return SimulatedFailureProvider(provider, runtime.provider_simulation)
    return provider


def _create_base_provider(
    provider_name: str,
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

        return AnthropicProvider(api_key=api_key)

    if provider_name == "ollama":
        return OllamaProvider(base_url=settings.ollama_base_url)

    raise ValueError(f"Unsupported AI provider: {provider_name}")
