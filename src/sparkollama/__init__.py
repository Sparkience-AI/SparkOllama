"""SparkOllama local chat application."""

from sparkollama.models import ChatMessage, ModelInfo
from sparkollama.service import ChatService, ConversationPolicy

__version__ = "0.1.0"

__all__ = ["ChatMessage", "ChatService", "ConversationPolicy", "ModelInfo"]
