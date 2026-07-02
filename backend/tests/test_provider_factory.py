"""Provider factory tests for OpenAI and Gemini."""

from __future__ import annotations

import pytest

from app.ai.providers.factory import create_provider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.groq import GroqProvider
from app.ai.providers.openai import OpenAIProvider
from app.core.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        anthropic_api_key="anthropic-dev",
        openai_api_key="openai-dev",
        gemini_api_key="gemini-dev",
        groq_api_key="groq-dev",
    )


def test_create_openai_provider_with_credentials(settings: Settings) -> None:
    provider = create_provider(
        "openai",
        {"api_key": "workspace-openai-key"},
        settings,
        allow_dev_fallback=False,
    )
    assert isinstance(provider, OpenAIProvider)


def test_create_openai_provider_uses_dev_fallback(settings: Settings) -> None:
    provider = create_provider("openai", None, settings, allow_dev_fallback=True)
    assert isinstance(provider, OpenAIProvider)


def test_create_openai_provider_requires_credentials(settings: Settings) -> None:
    with pytest.raises(ValueError, match="OpenAI"):
        create_provider("openai", None, settings, allow_dev_fallback=False)


def test_create_gemini_provider_with_credentials(settings: Settings) -> None:
    provider = create_provider(
        "gemini",
        {"api_key": "workspace-gemini-key"},
        settings,
        allow_dev_fallback=False,
    )
    assert isinstance(provider, GeminiProvider)


def test_create_gemini_provider_uses_dev_fallback(settings: Settings) -> None:
    provider = create_provider("gemini", None, settings, allow_dev_fallback=True)
    assert isinstance(provider, GeminiProvider)


def test_create_gemini_provider_requires_credentials(settings: Settings) -> None:
    with pytest.raises(ValueError, match="Gemini"):
        create_provider("gemini", None, settings, allow_dev_fallback=False)


def test_create_groq_provider_with_credentials(settings: Settings) -> None:
    provider = create_provider(
        "groq",
        {"api_key": "workspace-groq-key"},
        settings,
        allow_dev_fallback=False,
    )
    assert isinstance(provider, GroqProvider)


def test_create_groq_provider_uses_dev_fallback(settings: Settings) -> None:
    provider = create_provider("groq", None, settings, allow_dev_fallback=True)
    assert isinstance(provider, GroqProvider)


def test_create_groq_provider_requires_credentials(settings: Settings) -> None:
    with pytest.raises(ValueError, match="Groq"):
        create_provider("groq", None, settings, allow_dev_fallback=False)
