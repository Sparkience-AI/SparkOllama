from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pytest

from sparkollama.models import ChatMessage
from sparkollama.providers import (
    EndpointPolicyError,
    OllamaGenerationError,
    OllamaProtocolError,
    OllamaProvider,
    OllamaUnavailableError,
    validate_loopback_endpoint,
)


class FakeClient:
    def __init__(self, models: Any = None, chunks: Iterable[Any] = ()) -> None:
        self.models = {"models": []} if models is None else models
        self.chunks = chunks
        self.received_messages: list[dict[str, str]] | None = None

    def list(self) -> Any:
        return self.models

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        stream: bool,
    ) -> Iterable[Any]:
        assert model == "tiny"
        assert stream is True
        self.received_messages = messages
        return self.chunks


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://127.0.0.1:11434",
        "http://localhost:11434/",
        "https://[::1]:11434",
    ],
)
def test_loopback_endpoint_policy_accepts_local_hosts(endpoint: str) -> None:
    assert validate_loopback_endpoint(endpoint)


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://0.0.0.0:11434",
        "http://192.168.1.5:11434",
        "https://ollama.example.com:11434",
        "http://localhost:11434/api/chat",
        "http://user:secret@localhost:11434",
        "http://localhost:not-a-port",
        "http://localhost:70000",
        "file:///tmp/ollama.sock",
    ],
)
def test_loopback_endpoint_policy_rejects_remote_or_ambiguous_hosts(endpoint: str) -> None:
    with pytest.raises(EndpointPolicyError):
        validate_loopback_endpoint(endpoint)


def test_model_list_supports_current_and_legacy_response_names() -> None:
    client = FakeClient(
        models={
            "models": [
                {"model": "zeta", "digest": "abc", "size": 12},
                {"name": "Alpha"},
            ]
        }
    )

    result = OllamaProvider(client=client).list_models()

    assert [model.name for model in result] == ["Alpha", "zeta"]
    assert result[1].digest == "abc"
    assert result[1].size_bytes == 12


def test_model_list_translates_connection_failures() -> None:
    class FailingClient(FakeClient):
        def list(self) -> Any:
            raise ConnectionError("daemon unavailable")

    with pytest.raises(OllamaUnavailableError, match="loopback"):
        OllamaProvider(client=FailingClient()).list_models()


def test_model_list_rejects_malformed_response() -> None:
    with pytest.raises(OllamaProtocolError):
        OllamaProvider(client=FakeClient(models={})).list_models()


def test_stream_forwards_typed_messages_and_yields_content() -> None:
    client = FakeClient(chunks=[{"message": {"content": "hello"}}, {"message": {"content": ""}}])
    provider = OllamaProvider(client=client)

    result = list(provider.stream_chat("tiny", [ChatMessage("user", "hi")]))

    assert result == ["hello"]
    assert client.received_messages == [{"role": "user", "content": "hi"}]


def test_stream_preserves_partial_output_then_translates_failure() -> None:
    def failing_chunks() -> Iterable[dict[str, dict[str, str]]]:
        yield {"message": {"content": "partial"}}
        raise ConnectionError("lost connection")

    stream = OllamaProvider(client=FakeClient(chunks=failing_chunks())).stream_chat(
        "tiny", [ChatMessage("user", "hi")]
    )

    assert next(stream) == "partial"
    with pytest.raises(OllamaGenerationError, match="stopped"):
        next(stream)


def test_stream_rejects_malformed_chunks() -> None:
    stream = OllamaProvider(client=FakeClient(chunks=[{"done": False}])).stream_chat(
        "tiny", [ChatMessage("user", "hi")]
    )

    with pytest.raises(OllamaProtocolError):
        next(stream)
