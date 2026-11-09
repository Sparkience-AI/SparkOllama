"""Streamlit user interface for the tested SparkOllama core."""

from __future__ import annotations

import secrets
from typing import cast

import streamlit as st

from sparkollama.models import ChatMessage
from sparkollama.providers import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OPENAI_MODEL,
    AnthropicProvider,
    ChatProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
    SparkOllamaError,
)
from sparkollama.service import ChatService, managed_stream
from sparkollama.session import credential_fingerprint


def _messages() -> list[ChatMessage]:
    raw = st.session_state.setdefault("sparkollama_messages", [])
    return [ChatMessage(role=item["role"], content=item["content"]) for item in raw]


def _save_messages(messages: list[ChatMessage]) -> None:
    st.session_state.sparkollama_messages = [message.as_provider_message() for message in messages]


def _render_message(message: ChatMessage) -> None:
    with st.chat_message(message.role):
        st.markdown(message.content, unsafe_allow_html=False)


CLOUD_PROVIDERS = {
    "Google Gemini": ("Google Gemini API key", DEFAULT_GEMINI_MODEL, GeminiProvider),
    "OpenAI": ("OpenAI API key", DEFAULT_OPENAI_MODEL, OpenAIProvider),
    "Anthropic Claude": ("Anthropic API key", DEFAULT_ANTHROPIC_MODEL, AnthropicProvider),
}


def _credential_salt() -> bytes:
    salt = st.session_state.get("sparkollama_credential_salt")
    if not isinstance(salt, bytes) or len(salt) < 16:
        salt = secrets.token_bytes(32)
        st.session_state.sparkollama_credential_salt = salt
    return salt


def _configure_provider() -> tuple[ChatProvider, str, str, str] | None:
    provider_name = st.selectbox(
        "Provider",
        ["Local Ollama", *CLOUD_PROVIDERS],
        help="Local Ollama is the default. Cloud providers require your own key and consent.",
    )
    if provider_name == "Local Ollama":
        provider: ChatProvider = OllamaProvider()
        try:
            models = provider.list_models()
        except SparkOllamaError as exc:
            st.error(str(exc))
            st.info(
                "Start Ollama, then reload this page. The default endpoint is "
                "http://127.0.0.1:11434."
            )
            return None
        if not models:
            st.warning("Ollama is running, but no local models are installed.")
            st.code("ollama pull llama3.2", language="shell")
            return None
        names = [model.name for model in models]
        selected = st.selectbox("Local model", names)
        return provider, provider_name, selected, f"{provider_name}:{selected}"

    key_label, default_model, provider_type = CLOUD_PROVIDERS[provider_name]
    api_key = st.text_input(key_label, type="password", key=f"key-{provider_name}")
    model = st.text_input(
        "Model ID",
        value=default_model,
        key=f"model-{provider_name}",
        help="Use a model ID available to your provider account.",
    ).strip()
    consent = st.checkbox(
        f"Send this session's messages to {provider_name}",
        key=f"consent-{provider_name}",
    )
    if not api_key or not consent:
        st.info("Enter a key and confirm cloud transmission to start this provider session.")
        return None
    try:
        provider = cast(ChatProvider, provider_type(api_key, model))
    except SparkOllamaError as exc:
        st.error(str(exc))
        return None
    key_identity = credential_fingerprint(api_key, _credential_salt())
    return provider, provider_name, model, f"{provider_name}:{model}:{key_identity}"


def run() -> None:
    st.set_page_config(page_title="SparkOllama", page_icon="🤖", layout="wide")
    st.title("SparkOllama")
    st.caption("Local Ollama by default, with explicit session-only BYOK cloud options.")

    configured = _configure_provider()
    if configured is None:
        return
    provider, provider_name, selected_model, session_identity = configured
    service = ChatService(provider)

    messages = _messages()
    if st.session_state.get("sparkollama_selection") not in {None, session_identity}:
        messages = []
        _save_messages(messages)
        st.info(
            "The conversation was cleared because the provider, model, or cloud account changed."
        )
    st.session_state.sparkollama_selection = session_identity

    if st.button("Clear current chat", disabled=not messages):
        messages = []
        _save_messages(messages)
        st.rerun()

    for message in messages:
        _render_message(message)

    prompt = st.chat_input(f"Message {provider_name}", max_chars=8_000)
    if not prompt:
        return

    messages.append(ChatMessage(role="user", content=prompt))
    _render_message(messages[-1])

    partial: list[str] = []
    with st.chat_message("assistant"):
        output = st.empty()
        try:
            prepared, stream = service.stream_reply(selected_model, messages)
            if prepared.dropped_messages:
                st.caption(
                    f"Used the newest {len(prepared.messages)} messages; "
                    f"omitted {prepared.dropped_messages} older messages to bound local context."
                )
            with managed_stream(stream):
                for chunk in stream:
                    remaining = service.response_character_limit - sum(
                        len(part) for part in partial
                    )
                    if remaining <= 0:
                        st.warning(
                            "The response reached the session character limit and was stopped."
                        )
                        break
                    partial.append(chunk[:remaining])
                    output.markdown("".join(partial), unsafe_allow_html=False)
                    if len(chunk) > remaining:
                        st.warning(
                            "The response reached the session character limit and was stopped."
                        )
                        break
        except SparkOllamaError as exc:
            if partial:
                st.warning(f"{exc} The partial response remains in this session.")
            else:
                st.error(str(exc))

    if partial:
        messages.append(ChatMessage(role="assistant", content="".join(partial)))
        _save_messages(list(service.retain_session(messages)))


if __name__ == "__main__":
    run()
