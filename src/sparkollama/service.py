"""Framework-independent SparkOllama application service."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from sparkollama.models import ChatMessage, ModelInfo
from sparkollama.providers import ChatProvider, SparkOllamaError


class ConversationValidationError(SparkOllamaError):
    pass


@dataclass(frozen=True, slots=True)
class PreparedConversation:
    messages: tuple[ChatMessage, ...]
    dropped_messages: int


@dataclass(frozen=True, slots=True)
class ConversationPolicy:
    max_messages: int = 25
    max_characters: int = 32_000
    max_prompt_characters: int = 8_000
    max_response_characters: int = 16_000

    @staticmethod
    def _validate_alternating(messages: Sequence[ChatMessage], *, final_role: str) -> None:
        if not messages:
            raise ConversationValidationError("The conversation cannot be empty.")
        expected = "user"
        for message in messages:
            if message.role != expected:
                raise ConversationValidationError(
                    "Conversation messages must be complete alternating user/assistant turns."
                )
            expected = "assistant" if expected == "user" else "user"
        if messages[-1].role != final_role:
            raise ConversationValidationError(
                f"The conversation must end with an {final_role} message."
            )

    def _trim_complete_turns(self, messages: Sequence[ChatMessage]) -> list[ChatMessage]:
        selected = list(messages)
        while len(selected) > (1 if selected[-1].role == "user" else 2) and (
            len(selected) > self.max_messages
            or sum(len(message.content) for message in selected) > self.max_characters
        ):
            del selected[:2]
        return selected

    def prepare(self, messages: Sequence[ChatMessage]) -> PreparedConversation:
        if not messages:
            raise ConversationValidationError("Enter a message before starting generation.")
        self._validate_alternating(messages, final_role="user")
        if not messages[-1].content.strip():
            raise ConversationValidationError("The user message cannot be empty.")
        if len(messages[-1].content) > self.max_prompt_characters:
            raise ConversationValidationError(
                f"The latest message exceeds the {self.max_prompt_characters:,}-character limit."
            )

        selected = self._trim_complete_turns(messages)
        if sum(len(message.content) for message in selected) > self.max_characters:
            raise ConversationValidationError(
                f"The latest message exceeds the {self.max_characters:,}-character context limit."
            )
        return PreparedConversation(
            messages=tuple(selected),
            dropped_messages=len(messages) - len(selected),
        )

    def retain_session(self, messages: Sequence[ChatMessage]) -> tuple[ChatMessage, ...]:
        """Keep bounded, complete user/assistant turns in Streamlit session state."""

        self._validate_alternating(messages, final_role="assistant")
        selected = self._trim_complete_turns(messages)
        if sum(len(message.content) for message in selected) > self.max_characters:
            raise ConversationValidationError(
                "The latest conversation turn exceeds session limits."
            )
        return tuple(selected)


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
    ) -> tuple[PreparedConversation, Iterator[str]]:
        if not model.strip():
            raise ConversationValidationError("Select an installed Ollama model.")
        prepared = self._policy.prepare(messages)
        stream = self._provider.stream_chat(model, prepared.messages)
        return prepared, stream

    @property
    def response_character_limit(self) -> int:
        return self._policy.max_response_characters

    def retain_session(self, messages: Sequence[ChatMessage]) -> tuple[ChatMessage, ...]:
        return self._policy.retain_session(messages)
