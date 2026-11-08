from __future__ import annotations

from collections.abc import Iterator, Sequence

import pytest

from sparkollama.mcp_tools import generate_local, list_local_models, local_status
from sparkollama.models import ChatMessage, ModelInfo
from sparkollama.service import ChatService, ConversationPolicy


class FakeProvider:
    def __init__(self, chunks: list[str] | None = None) -> None:
        self.chunks = chunks or ["private ", "answer"]

    def list_models(self) -> list[ModelInfo]:
        return [ModelInfo("tiny", "abc", 12)]

    def stream_chat(self, model: str, messages: Sequence[ChatMessage]) -> Iterator[str]:
        assert model == "tiny"
        assert list(messages) == [ChatMessage("user", "hello")]
        yield from self.chunks


def factory(chunks: list[str] | None = None) -> ChatService:
    return ChatService(FakeProvider(chunks))


def test_status_declares_local_nonpersistent_boundary() -> None:
    status = local_status()
    assert status["transport"] == "stdio"
    assert status["network_scope"] == "loopback-only"
    assert status["cloud_providers_exposed"] is False


def test_mcp_lists_models_and_generates_without_history() -> None:
    models = list_local_models(service_factory=factory)
    assert models["count"] == 1
    assert models["truncated"] is False
    result = generate_local("tiny", "hello", service_factory=factory)
    assert result["response"] == "private answer"
    assert result["local_only"] is True
    assert result["persisted"] is False


def test_mcp_enforces_prompt_and_response_bounds() -> None:
    with pytest.raises(ValueError, match="8,000-character"):
        generate_local("tiny", "x" * 8_001, service_factory=factory)
    policy = ConversationPolicy(max_response_characters=3)
    with pytest.raises(ValueError, match="response exceeded"):
        generate_local(
            "tiny",
            "hello",
            service_factory=lambda: ChatService(FakeProvider(["four"]), policy),
        )


def test_mcp_rejects_uninstalled_or_oversized_model_names() -> None:
    with pytest.raises(ValueError, match="already installed"):
        generate_local("unknown", "hello", service_factory=factory)
    with pytest.raises(ValueError, match="model name exceeds"):
        generate_local("x" * 201, "hello", service_factory=factory)


def test_mcp_bounds_model_list_output() -> None:
    class ManyModelsProvider(FakeProvider):
        def list_models(self) -> list[ModelInfo]:
            return [ModelInfo(f"model-{index}-" + "x" * 300) for index in range(101)]

    result = list_local_models(service_factory=lambda: ChatService(ManyModelsProvider()))
    assert result["count"] == 100
    assert result["total_count"] == 101
    assert result["truncated"] is True
    assert all(len(model["name"]) <= 200 for model in result["models"])
