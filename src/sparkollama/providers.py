"""Provider boundaries for local Ollama and explicit BYOK cloud sessions."""

from __future__ import annotations

import builtins
from collections.abc import Iterable, Iterator, Sequence
from typing import Any, Protocol, cast
from urllib.parse import urlsplit

import ollama

from sparkollama.models import ChatMessage, ModelInfo

DEFAULT_OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
DEFAULT_OPENAI_MODEL = "gpt-6-luna"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5-5"


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


class ProviderConfigurationError(SparkOllamaError):
    pass


class CloudGenerationError(SparkOllamaError):
    pass


def validate_loopback_endpoint(endpoint: str) -> str:
    """Accept only an HTTP(S) Ollama endpoint on the local machine."""

    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError as exc:
        raise EndpointPolicyError("The Ollama endpoint contains an invalid host or port.") from exc
    if parsed.scheme not in {"http", "https"}:
        raise EndpointPolicyError("The Ollama endpoint must use HTTP or HTTPS.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise EndpointPolicyError("The Ollama endpoint must not contain credentials or parameters.")
    if parsed.path not in {"", "/"}:
        raise EndpointPolicyError("The Ollama endpoint must not contain a path.")
    if parsed.hostname not in {"127.0.0.1", "::1", "localhost"}:
        raise EndpointPolicyError("SparkOllama supports loopback Ollama endpoints only.")
    if port is None or not 1 <= port <= 65_535:
        raise EndpointPolicyError("The Ollama endpoint must include a port from 1 to 65535.")
    return endpoint.rstrip("/")


def _value(item: Any, *names: str) -> Any:
    for name in names:
        if isinstance(item, dict) and name in item:
            return item[name]
        value = getattr(item, name, None)
        if value is not None:
            return value
    return None


def _close_if_supported(stream: object) -> None:
    close = getattr(stream, "close", None)
    if callable(close):
        close()


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
    ) -> Iterator[str]:
        try:
            chunks = self._client.chat(
                model=model,
                messages=[message.as_provider_message() for message in messages],
                stream=True,
            )
            try:
                for chunk in chunks:
                    message = _value(chunk, "message")
                    content = _value(message, "content") if message is not None else None
                    if not isinstance(content, str):
                        raise OllamaProtocolError(
                            "Ollama returned an unexpected streaming response."
                        )
                    if content:
                        yield content
            finally:
                _close_if_supported(chunks)
        except SparkOllamaError:
            raise
        except Exception as exc:
            raise OllamaGenerationError(
                "Local generation stopped before a complete response was received."
            ) from exc


class StaticModelProvider:
    """Shared model-list behavior for one explicitly configured cloud model."""

    provider_name = "Cloud provider"

    def __init__(self, model: str) -> None:
        normalized = model.strip()
        if not normalized:
            raise ProviderConfigurationError("Enter a model ID before starting a cloud session.")
        self.model = normalized

    def list_models(self) -> list[ModelInfo]:
        return [ModelInfo(self.model)]

    def _translate_failure(self, exc: Exception) -> CloudGenerationError:
        return CloudGenerationError(
            f"{self.provider_name} generation stopped before a complete response was received."
        )


class GeminiProvider(StaticModelProvider):
    provider_name = "Google Gemini"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_GEMINI_MODEL,
        *,
        client: Any | None = None,
    ) -> None:
        super().__init__(model)
        if not api_key.strip():
            raise ProviderConfigurationError("Enter a Google Gemini API key.")
        if client is None:
            try:
                from google import genai
            except ImportError as exc:
                raise ProviderConfigurationError(
                    "Install cloud providers with `uv sync --extra cloud`."
                ) from exc
            client = genai.Client(api_key=api_key)
        self._client = client

    def stream_chat(self, model: str, messages: Sequence[ChatMessage]) -> Iterator[str]:
        try:
            contents = [
                {
                    "role": "model" if message.role == "assistant" else "user",
                    "parts": [{"text": message.content}],
                }
                for message in messages
            ]
            chunks = self._client.models.generate_content_stream(
                model=model,
                contents=contents,
            )
            try:
                for chunk in chunks:
                    text = getattr(chunk, "text", None)
                    if isinstance(text, str) and text:
                        yield text
            finally:
                _close_if_supported(chunks)
        except SparkOllamaError:
            raise
        except Exception as exc:
            raise self._translate_failure(exc) from exc


class OpenAIProvider(StaticModelProvider):
    provider_name = "OpenAI"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_OPENAI_MODEL,
        *,
        client: Any | None = None,
    ) -> None:
        super().__init__(model)
        if not api_key.strip():
            raise ProviderConfigurationError("Enter an OpenAI API key.")
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ProviderConfigurationError(
                    "Install cloud providers with `uv sync --extra cloud`."
                ) from exc
            client = OpenAI(api_key=api_key)
        self._client = client

    def stream_chat(self, model: str, messages: Sequence[ChatMessage]) -> Iterator[str]:
        try:
            stream = self._client.responses.create(
                model=model,
                input=[message.as_provider_message() for message in messages],
                stream=True,
                store=False,
            )
            try:
                for event in stream:
                    if getattr(event, "type", None) == "response.output_text.delta":
                        delta = getattr(event, "delta", None)
                        if isinstance(delta, str) and delta:
                            yield delta
            finally:
                _close_if_supported(stream)
        except SparkOllamaError:
            raise
        except Exception as exc:
            raise self._translate_failure(exc) from exc


class AnthropicProvider(StaticModelProvider):
    provider_name = "Anthropic Claude"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_ANTHROPIC_MODEL,
        *,
        client: Any | None = None,
    ) -> None:
        super().__init__(model)
        if not api_key.strip():
            raise ProviderConfigurationError("Enter an Anthropic API key.")
        if client is None:
            try:
                from anthropic import Anthropic
            except ImportError as exc:
                raise ProviderConfigurationError(
                    "Install cloud providers with `uv sync --extra cloud`."
                ) from exc
            client = Anthropic(api_key=api_key)
        self._client = client

    def stream_chat(self, model: str, messages: Sequence[ChatMessage]) -> Iterator[str]:
        try:
            with self._client.messages.stream(
                model=model,
                max_tokens=4_096,
                messages=[message.as_provider_message() for message in messages],
            ) as stream:
                yield from stream.text_stream
        except SparkOllamaError:
            raise
        except Exception as exc:
            raise self._translate_failure(exc) from exc
