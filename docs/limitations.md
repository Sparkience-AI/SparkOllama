# Current limitations

SparkOllama is an alpha local-first chat client, not a hosted service.

- Ollama is restricted to loopback; remote Ollama endpoints are not supported.
- Gemini, OpenAI, and Anthropic require provider-specific network access, account availability,
  quotas, terms, and a user-supplied key.
- Conversation history exists only in the current Streamlit session.
- Context is bounded by message and character limits, not a model-specific tokenizer.
- The current Streamlit interface cannot reliably cancel an in-flight provider request. Ollama has
  a 60-second client timeout; equivalent configurable cloud timeouts remain future hardening work.
- Provider stream iterators are explicitly closed when rendering finishes, fails, or reaches the
  response limit, but a provider call already blocked on network I/O may still wait for its timeout.
- Partial streamed output is retained in the session when the connection fails.
- Model quality, safety, licensing, context size, availability, and cost depend on the selected
  provider and model.
- Saved conversations, remote Ollama endpoints, tool calling, and public hosting are intentionally
  out of scope.
