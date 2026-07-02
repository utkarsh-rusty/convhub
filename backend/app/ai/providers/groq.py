from openai import AsyncOpenAI

from app.ai.providers.openai import OpenAIProvider

GROQ_API_BASE = "https://api.groq.com/openai/v1"


class GroqProvider(OpenAIProvider):
    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=GROQ_API_BASE)
