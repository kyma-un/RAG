import os
from typing import Optional

from .BaseLLM import BaseLLM
from .GeminiLLM import GeminiLLM
from .OllamaLLM import OllamaLLM


class FallbackLLM(BaseLLM):
    def __init__(
        self,
        primary: BaseLLM,
        primary_provider: str,
        fallback: Optional[BaseLLM] = None,
        fallback_provider: Optional[str] = None,
    ):
        self.primary = primary
        self.primary_provider = primary_provider
        self.fallback = fallback
        self.fallback_provider = fallback_provider

    @staticmethod
    def _is_error_response(response: str) -> bool:
        if not isinstance(response, str):
            return False
        normalized = response.strip().lower()
        return normalized.startswith("error generating response:")

    def generate(self, prompt: str) -> str:
        primary_response = self.primary.generate(prompt)
        if not self._is_error_response(primary_response):
            return primary_response

        if self.fallback is None:
            return primary_response

        fallback_response = self.fallback.generate(prompt)
        if not self._is_error_response(fallback_response):
            return fallback_response

        return (
            f"Primary provider '{self.primary_provider}' and fallback provider "
            f"'{self.fallback_provider}' failed. Last error: {fallback_response}"
        )


def _build_provider(provider: str) -> BaseLLM:
    normalized = (provider or "").strip().lower()

    match normalized:
        case "gemini":
            return GeminiLLM()
        case "ollama":
            return OllamaLLM(model_name=os.getenv("OLLAMA_MODEL", "llama3"))
        case _:
            raise ValueError(f"Unsupported LLM provider: {provider}")


def get_llm():
    primary_provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    fallback_provider = os.getenv("LLM_FALLBACK_PROVIDER", "").strip().lower()

    primary = _build_provider(primary_provider)

    if not fallback_provider or fallback_provider == primary_provider:
        return primary

    fallback = _build_provider(fallback_provider)
    return FallbackLLM(
        primary=primary,
        primary_provider=primary_provider,
        fallback=fallback,
        fallback_provider=fallback_provider,
    )
    
