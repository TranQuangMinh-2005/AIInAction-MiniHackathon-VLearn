"""Chat provider used by all Agent nodes."""

from agent.providers import build_chat_model


# Auto-selects OpenAI when configured, otherwise Gemini.
llm = build_chat_model()
