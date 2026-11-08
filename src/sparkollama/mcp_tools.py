"""Bounded functions exposed by the optional local MCP server."""

from __future__ import annotations

from dataclasses import asdict
from typing import Protocol

from sparkollama.models import ChatMessage, ModelInfo
from sparkollama.providers import DEFAULT_OLLAMA_ENDPOINT, OllamaProvider
from sparkollama.service import ChatService, ConversationValidationError

MAX_LISTED_MODELS = 100
MAX_MODEL_NAME_CHARACTERS = 200
MAX_DIGEST_CHARACTERS = 256


class LocalServiceFactory(Protocol):
    def __call__(self) -> ChatService: ...


def default_service() -> ChatService:
    return ChatService(OllamaProvider())


def local_status() -> dict[str, object]:
    """Describe the fixed MCP privacy boundary without probing the network."""

    return {
        "status": "configured",
        "transport": "stdio",
        "provider": "ollama",
        "endpoint": DEFAULT_OLLAMA_ENDPOINT,
        "network_scope": "loopback-only",
        "persistence": "none",
        "cloud_providers_exposed": False,
    }


def list_local_models(
    *, service_factory: LocalServiceFactory = default_service
) -> dict[str, object]:
    models: list[ModelInfo] = service_factory().available_models()
    bounded = [
        {
            **asdict(model),
            "name": model.name[:MAX_MODEL_NAME_CHARACTERS],
            "digest": model.digest[:MAX_DIGEST_CHARACTERS] if model.digest else None,
        }
        for model in models[:MAX_LISTED_MODELS]
    ]
    return {
        "models": bounded,
        "count": len(bounded),
        "total_count": len(models),
        "truncated": len(models) > MAX_LISTED_MODELS,
    }


def generate_local(
    model: str,
    prompt: str,
    *,
    service_factory: LocalServiceFactory = default_service,
) -> dict[str, object]:
    """Run one bounded, stateless local generation request."""

    normalized_model = model.strip()
    if not normalized_model:
        raise ValueError("Choose an installed local model.")
    if len(normalized_model) > MAX_MODEL_NAME_CHARACTERS:
        raise ValueError(
            f"The model name exceeds the {MAX_MODEL_NAME_CHARACTERS}-character MCP limit."
        )
    service = service_factory()
    installed_models = {item.name for item in service.available_models()}
    if normalized_model not in installed_models:
        raise ValueError("Choose a model already installed in the local Ollama service.")
    try:
        prepared, stream = service.stream_reply(normalized_model, [ChatMessage("user", prompt)])
    except ConversationValidationError as exc:
        raise ValueError(str(exc)) from exc
    parts: list[str] = []
    total = 0
    limit = service.response_character_limit
    for part in stream:
        total += len(part)
        if total > limit:
            raise ValueError(f"The response exceeded the {limit:,}-character MCP limit.")
        parts.append(part)
    response = "".join(parts).strip()
    if not response:
        raise ValueError("Ollama returned an empty response.")
    return {
        "model": normalized_model,
        "response": response,
        "dropped_messages": prepared.dropped_messages,
        "local_only": True,
        "persisted": False,
    }
