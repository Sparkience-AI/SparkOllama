"""Streamlit user interface for the tested SparkOllama core."""

from __future__ import annotations

import streamlit as st

from sparkollama.models import ChatMessage
from sparkollama.providers import OllamaProvider, SparkOllamaError
from sparkollama.service import ChatService


def _messages() -> list[ChatMessage]:
    raw = st.session_state.setdefault("sparkollama_messages", [])
    return [ChatMessage(role=item["role"], content=item["content"]) for item in raw]


def _save_messages(messages: list[ChatMessage]) -> None:
    st.session_state.sparkollama_messages = [message.as_provider_message() for message in messages]


def _render_message(message: ChatMessage) -> None:
    with st.chat_message(message.role):
        st.markdown(message.content, unsafe_allow_html=False)


def run() -> None:
    st.set_page_config(page_title="SparkOllama", page_icon="🤖", layout="wide")
    st.title("SparkOllama")
    st.caption("Private, session-only chat with models running on your local Ollama service.")

    service = ChatService(OllamaProvider())
    try:
        models = service.available_models()
    except SparkOllamaError as exc:
        st.error(str(exc))
        st.info(
            "Start Ollama, then reload this page. The default endpoint is http://127.0.0.1:11434."
        )
        st.stop()

    if not models:
        st.warning("Ollama is running, but no local models are installed.")
        st.code("ollama pull llama3.2", language="shell")
        st.stop()

    names = [model.name for model in models]
    previous_model = st.session_state.get("sparkollama_selected_model")
    if previous_model not in names:
        previous_model = names[0]
    selected_model = st.selectbox(
        "Local model",
        names,
        index=names.index(previous_model),
        help="Changing models clears the current conversation to avoid mixing model contexts.",
    )

    messages = _messages()
    if st.session_state.get("sparkollama_selected_model") not in {None, selected_model}:
        messages = []
        _save_messages(messages)
        st.info("The conversation was cleared because the selected model changed.")
    st.session_state.sparkollama_selected_model = selected_model

    if st.button("Clear current chat", disabled=not messages):
        messages = []
        _save_messages(messages)
        st.rerun()

    for message in messages:
        _render_message(message)

    prompt = st.chat_input("Message your local model", max_chars=8_000)
    if not prompt:
        return

    messages.append(ChatMessage(role="user", content=prompt))
    _save_messages(messages)
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
            for chunk in stream:
                partial.append(chunk)
                output.markdown("".join(partial), unsafe_allow_html=False)
        except SparkOllamaError as exc:
            if partial:
                st.warning(f"{exc} The partial response remains in this session.")
            else:
                st.error(str(exc))

    if partial:
        messages.append(ChatMessage(role="assistant", content="".join(partial)))
        _save_messages(messages)
