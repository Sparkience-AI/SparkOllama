"""Provider boundary for the loopback Ollama service."""

from __future__ import annotations

import builtins
from collections.abc import Iterable, Iterator, Sequence
from typing import Any, Protocol, cast
from urllib.parse import urlsplit

import ollama

from sparkollama.models import ChatMessage, ModelInfo

DEFAULT_OLLAMA_ENDPOINT = "http://127.0.0.1:11434"


class CancellationSignal(Protocol):
    def is_set(self) -> bool: ...


class OllamaClient(Protocol):
    def list(self) -> Any: ...

    def chat(
        self,
        *,
        model: str,
        messages: builtins.list[dict[str, str]],
        stream: bool,
    ) -> Iterable[Any]: ...


class ChatProvider(Protocol):
    def list_models(self) -> list[ModelInfo]: ...

    def stream_chat(
        self,
        model: str,
        messages: Sequence[ChatMessage],
        cancellation: CancellationSignal | None = None,
    ) -> Iterator[str]: ...


class SparkOllamaError(RuntimeError):
    """Base class for safe, user-displayable application errors."""


class EndpointPolicyError(SparkOllamaError):
    pass


class OllamaUnavailableError(SparkOllamaError):
    pass


class OllamaProtocolError(SparkOllamaError):
    pass


class OllamaGenerationError(SparkOllamaError):
    pass


def validate_loopback_endpoint(endpoint: str) -> str:
    """Accept only an HTTP(S) Ollama endpoint on the local machine."""

    parsed = urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"}:
        raise EndpointPolicyError("The Ollama endpoint must use HTTP or HTTPS.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise EndpointPolicyError("The Ollama endpoint must not contain credentials or parameters.")
    if parsed.path not in {"", "/"}:
        raise EndpointPolicyError("The Ollama endpoint must not contain a path.")
    if parsed.hostname not in {"127.0.0.1", "::1", "localhost"}:
        raise EndpointPolicyError("SparkOllama supports loopback Ollama endpoints only.")
    if parsed.port is None:
        raise EndpointPolicyError("The Ollama endpoint must include an explicit port.")
    return endpoint.rstrip("/")


def _value(item: Any, *names: str) -> Any:
    for name in names:
        if isinstance(item, dict) and name in item:
            return item[name]
        value = getattr(item, name, None)
        if value is not None:
            return value
    return None


class OllamaProvider:
    """Translate the Ollama Python client into the application provider contract."""

    def __init__(
        self,
        endpoint: str = DEFAULT_OLLAMA_ENDPOINT,
        *,
        timeout_seconds: float = 60.0,
        client: OllamaClient | None = None,
    ) -> None:
        self.endpoint = validate_loopback_endpoint(endpoint)
        self._client = client or cast(
            OllamaClient,
            ollama.Client(host=self.endpoint, timeout=timeout_seconds),
        )

    def list_models(self) -> list[ModelInfo]:
        try:
            response = self._client.list()
            raw_models = _value(response, "models")
            if raw_models is None:
                raise OllamaProtocolError("Ollama returned an unexpected model-list response.")
            models: list[ModelInfo] = []
            for raw in raw_models:
                name = _value(raw, "model", "name")
                if not isinstance(name, str) or not name.strip():
                    raise OllamaProtocolError("Ollama returned a model without a valid name.")
                digest = _value(raw, "digest")
                size = _value(raw, "size")
                models.append(
                    ModelInfo(
                        name=name,
                        digest=digest if isinstance(digest, str) else None,
                        size_bytes=size if isinstance(size, int) else None,
                    )
                )
            return sorted(models, key=lambda model: model.name.casefold())
        except SparkOllamaError:
            raise
        except Exception as exc:
            raise OllamaUnavailableError(
                "Ollama is not reachable on the local loopback endpoint."
            ) from exc

    def stream_chat(
        self,
        model: str,
        messages: Sequence[ChatMessage],
        cancellation: CancellationSignal | None = None,
    ) -> Iterator[str]:
        try:
            chunks = self._client.chat(
                model=model,
                messages=[message.as_provider_message() for message in messages],
                stream=True,
            )
            for chunk in chunks:
                if cancellation is not None and cancellation.is_set():
                    return
                message = _value(chunk, "message")
                content = _value(message, "content") if message is not None else None
                if not isinstance(content, str):
                    raise OllamaProtocolError("Ollama returned an unexpected streaming response.")
                if content:
                    yield content
        except SparkOllamaError:
            raise
        except Exception as exc:
            raise OllamaGenerationError(
                "Local generation stopped before a complete response was received."
            ) from exc
