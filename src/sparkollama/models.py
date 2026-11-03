"""Typed values shared across SparkOllama layers."""

from dataclasses import dataclass
from typing import Literal

ChatRole = Literal["user", "assistant", "system"]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: ChatRole
    content: str

    def as_provider_message(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True, slots=True)
class ModelInfo:
    name: str
    digest: str | None = None
    size_bytes: int | None = None
