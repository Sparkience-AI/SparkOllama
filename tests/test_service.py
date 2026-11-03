from __future__ import annotations

from collections.abc import Iterator, Sequence

import pytest

from sparkollama.models import ChatMessage, ModelInfo
from sparkollama.service import ChatService, ConversationPolicy, ConversationValidationError


class FakeProvider:
    def __init__(self) -> None:
        self.received: Sequence[ChatMessage] = []

    def list_models(self) -> list[ModelInfo]:
        return [ModelInfo("tiny")]

    def stream_chat(
        self,
        model: str,
        messages: Sequence[ChatMessage],
    ) -> Iterator[str]:
        self.received = messages
        yield f"reply from {model}"


def test_policy_keeps_complete_turns_without_orphaning_assistant_messages() -> None:
    policy = ConversationPolicy(max_messages=3, max_characters=20, max_prompt_characters=8)
    history = [
        ChatMessage("user", "one"),
        ChatMessage("assistant", "two"),
        ChatMessage("user", "three"),
        ChatMessage("assistant", "four"),
        ChatMessage("user", "five"),
    ]

    result = policy.prepare(history)

    assert result.messages == (
        ChatMessage("user", "three"),
        ChatMessage("assistant", "four"),
        ChatMessage("user", "five"),
    )
    assert result.dropped_messages == 2


def test_policy_bounds_complete_session_turns() -> None:
    policy = ConversationPolicy(max_messages=2, max_characters=100)
    history = [
        ChatMessage("user", "old"),
        ChatMessage("assistant", "answer"),
        ChatMessage("user", "new"),
        ChatMessage("assistant", "reply"),
    ]

    assert policy.retain_session(history) == (
        ChatMessage("user", "new"),
        ChatMessage("assistant", "reply"),
    )


@pytest.mark.parametrize(
    "messages",
    [
        [],
        [ChatMessage("assistant", "not a user turn")],
        [ChatMessage("user", "   ")],
    ],
)
def test_policy_rejects_invalid_latest_turn(messages: list[ChatMessage]) -> None:
    with pytest.raises(ConversationValidationError):
        ConversationPolicy().prepare(messages)


def test_policy_rejects_oversized_latest_prompt() -> None:
    with pytest.raises(ConversationValidationError, match="4-character"):
        ConversationPolicy(max_prompt_characters=4).prepare([ChatMessage("user", "12345")])


def test_service_uses_prepared_history() -> None:
    provider = FakeProvider()
    service = ChatService(
        provider,
        ConversationPolicy(max_messages=3, max_characters=100, max_prompt_characters=100),
    )
    history = [
        ChatMessage("user", "old"),
        ChatMessage("assistant", "answer"),
        ChatMessage("user", "new"),
    ]

    prepared, stream = service.stream_reply("tiny", history)

    assert list(stream) == ["reply from tiny"]
    assert provider.received == prepared.messages
    assert prepared.dropped_messages == 0


def test_service_requires_a_model() -> None:
    with pytest.raises(ConversationValidationError, match="Select"):
        ChatService(FakeProvider()).stream_reply(" ", [ChatMessage("user", "hello")])
