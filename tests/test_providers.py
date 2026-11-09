from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

import pytest

from sparkollama.models import ChatMessage
from sparkollama.providers import (
    AnthropicProvider,
    EndpointPolicyError,
    GeminiProvider,
    OllamaGenerationError,
    OllamaProtocolError,
    OllamaProvider,
    OllamaUnavailableError,
    OpenAIProvider,
    ProviderConfigurationError,
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


def test_gemini_stream_uses_direct_key_client_and_conversation_roles() -> None:
    class Models:
        def generate_content_stream(self, **kwargs: Any) -> Iterable[Any]:
            assert kwargs == {
                "model": "gemini-test",
                "contents": [
                    {"role": "user", "parts": [{"text": "hi"}]},
                    {"role": "model", "parts": [{"text": "hello"}]},
                    {"role": "user", "parts": [{"text": "again"}]},
                ],
            }
            return [type("Chunk", (), {"text": "answer"})()]

    client = type("GeminiClient", (), {"models": Models()})()
    provider = GeminiProvider("session-key", "gemini-test", client=client)

    result = list(
        provider.stream_chat(
            "gemini-test",
            [
                ChatMessage("user", "hi"),
                ChatMessage("assistant", "hello"),
                ChatMessage("user", "again"),
            ],
        )
    )

    assert result == ["answer"]


def test_openai_stream_uses_responses_api_without_storage() -> None:
    calls: list[dict[str, Any]] = []

    class Responses:
        def create(self, **kwargs: Any) -> Iterable[Any]:
            calls.append(kwargs)
            return [
                type(
                    "Event",
                    (),
                    {"type": "response.output_text.delta", "delta": "answer"},
                )()
            ]

    client = type("OpenAIClient", (), {"responses": Responses()})()
    provider = OpenAIProvider("session-key", "gpt-test", client=client)

    result = list(provider.stream_chat("gpt-test", [ChatMessage("user", "hi")]))

    assert result == ["answer"]
    assert calls == [
        {
            "model": "gpt-test",
            "input": [{"role": "user", "content": "hi"}],
            "stream": True,
            "store": False,
        }
    ]


def test_openai_stream_closes_the_sdk_iterator_when_consumption_stops() -> None:
    class Events(Iterator[Any]):
        def __init__(self) -> None:
            self.closed = False

        def __next__(self) -> Any:
            return type(
                "Event",
                (),
                {"type": "response.output_text.delta", "delta": "partial"},
            )()

        def close(self) -> None:
            self.closed = True

    events = Events()

    class Responses:
        def create(self, **kwargs: Any) -> Events:
            return events

    client = type("OpenAIClient", (), {"responses": Responses()})()
    stream = OpenAIProvider("session-key", "gpt-test", client=client).stream_chat(
        "gpt-test", [ChatMessage("user", "hi")]
    )

    assert next(stream) == "partial"
    stream.close()
    assert events.closed is True


def test_anthropic_stream_uses_messages_api() -> None:
    calls: list[dict[str, Any]] = []

    class Stream:
        text_stream = ["answer"]

        def __enter__(self) -> Stream:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

    class Messages:
        def stream(self, **kwargs: Any) -> Stream:
            calls.append(kwargs)
            return Stream()

    client = type("AnthropicClient", (), {"messages": Messages()})()
    provider = AnthropicProvider("session-key", "claude-test", client=client)

    assert list(provider.stream_chat("claude-test", [ChatMessage("user", "hi")])) == ["answer"]
    assert calls == [
        {
            "model": "claude-test",
            "max_tokens": 4_096,
            "messages": [{"role": "user", "content": "hi"}],
        }
    ]


@pytest.mark.parametrize("provider", [GeminiProvider, OpenAIProvider, AnthropicProvider])
def test_cloud_providers_reject_blank_session_keys(provider: Any) -> None:
    with pytest.raises(ProviderConfigurationError, match="key"):
        provider(" ", client=object())
