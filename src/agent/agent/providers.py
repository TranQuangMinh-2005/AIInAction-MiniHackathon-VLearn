"""Provider selection shared by the slide retriever and chat Agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from langchain_core.messages import BaseMessage

from agent.config import load_environment
from local_rag.config import Settings
from local_rag.service import RAGService

load_environment()


@dataclass
class ChatChunk:
    content: str


class GeminiChat:
    """Small adapter exposing the invoke/stream API used by the Agent nodes."""

    def __init__(self, model: str, temperature: float = 0.1) -> None:
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing. Add it to .env, "
                "src/agent/.env, or codebase/rag/.env."
            )
        self.client = genai.Client(api_key=api_key)
        self.model = model
        fallback_models = os.getenv(
            "AGENT_GEMINI_FALLBACK_MODELS",
            "gemini-3.1-flash-lite,gemini-2.5-flash-lite",
        )
        self.models = list(
            dict.fromkeys(
                [model]
                + [
                    item.strip()
                    for item in fallback_models.split(",")
                    if item.strip()
                ]
            )
        )
        self.temperature = temperature

    @staticmethod
    def _prompt(value: str | Iterable[BaseMessage]) -> tuple[str, str]:
        if isinstance(value, str):
            return "", value

        system_parts: list[str] = []
        content_parts: list[str] = []
        for message in value:
            text = str(getattr(message, "content", message))
            message_type = getattr(message, "type", "")
            if message_type == "system":
                system_parts.append(text)
            else:
                role = "Assistant" if message_type == "ai" else "User"
                content_parts.append(f"{role}: {text}")
        return "\n\n".join(system_parts), "\n\n".join(content_parts)

    def _config(self, system_instruction: str) -> dict:
        config: dict = {"temperature": self.temperature}
        if system_instruction:
            config["system_instruction"] = system_instruction
        return config

    @staticmethod
    def _can_fallback(exc: Exception) -> bool:
        code = getattr(exc, "code", getattr(exc, "status_code", None))
        return code in {429, 500, 503, 504}

    def invoke(self, value: str | Iterable[BaseMessage]) -> ChatChunk:
        system_instruction, prompt = self._prompt(value)
        for index, model in enumerate(self.models):
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=self._config(system_instruction),
                )
                return ChatChunk(content=(response.text or "").strip())
            except Exception as exc:
                has_fallback = index + 1 < len(self.models)
                if not has_fallback or not self._can_fallback(exc):
                    raise
        raise RuntimeError("No Gemini chat model was available")

    def stream(self, value: str | Iterable[BaseMessage]):
        system_instruction, prompt = self._prompt(value)
        for index, model in enumerate(self.models):
            yielded = False
            try:
                for chunk in self.client.models.generate_content_stream(
                    model=model,
                    contents=prompt,
                    config=self._config(system_instruction),
                ):
                    if chunk.text:
                        yielded = True
                        yield ChatChunk(content=chunk.text)
                return
            except Exception as exc:
                has_fallback = index + 1 < len(self.models)
                if yielded or not has_fallback or not self._can_fallback(exc):
                    raise


def build_chat_model():
    settings = Settings.from_env()
    if settings.provider == "gemini":
        return GeminiChat(settings.chat_model)

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.chat_model,
        temperature=0.1,
    )


def build_embedding_model():
    """Reuse the exact embedding provider configured for the paper RAG."""
    return RAGService.from_env().embedder
