"""Framework-independent SparkOllama application service."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from sparkollama.models import ChatMessage, ModelInfo
from sparkollama.providers import CancellationSignal, ChatProvider, SparkOllamaError


class ConversationValidationError(SparkOllamaError):
    pass


@dataclass(frozen=True, slots=True)
class PreparedConversation:
    messages: tuple[ChatMessage, ...]
    dropped_messages: int


@dataclass(frozen=True, slots=True)
class ConversationPolicy:
    max_messages: int = 24
    max_characters: int = 32_000
    max_prompt_characters: int = 8_000

    def prepare(self, messages: Sequence[ChatMessage]) -> PreparedConversation:
        if not messages:
            raise ConversationValidationError("Enter a message before starting generation.")
        if messages[-1].role != "user":
            raise ConversationValidationError("The conversation must end with a user message.")
        if not messages[-1].content.strip():
            raise ConversationValidationError("The user message cannot be empty.")
        if len(messages[-1].content) > self.max_prompt_characters:
            raise ConversationValidationError(
                f"The latest message exceeds the {self.max_prompt_characters:,}-character limit."
            )

        selected = list(messages[-self.max_messages :])
        while (
            len(selected) > 1
            and sum(len(message.content) for message in selected) > self.max_characters
        ):
            selected.pop(0)
        if sum(len(message.content) for message in selected) > self.max_characters:
            raise ConversationValidationError(
                f"The latest message exceeds the {self.max_characters:,}-character context limit."
            )
        return PreparedConversation(
            messages=tuple(selected),
            dropped_messages=len(messages) - len(selected),
        )


class ChatService:
    def __init__(
        self,
        provider: ChatProvider,
        policy: ConversationPolicy | None = None,
    ) -> None:
        self._provider = provider
        self._policy = policy or ConversationPolicy()

    def available_models(self) -> list[ModelInfo]:
        return self._provider.list_models()

    def stream_reply(
        self,
        model: str,
        messages: Sequence[ChatMessage],
        cancellation: CancellationSignal | None = None,
    ) -> tuple[PreparedConversation, Iterator[str]]:
        if not model.strip():
            raise ConversationValidationError("Select an installed Ollama model.")
        prepared = self._policy.prepare(messages)
        stream = self._provider.stream_chat(model, prepared.messages, cancellation)
        return prepared, stream
