# Current limitations

SparkOllama is an alpha local chat client, not a hosted service.

- Only a loopback Ollama service is supported.
- Conversation history exists only in the current Streamlit session.
- Context is bounded by message and character limits, not a model-specific tokenizer.
- The provider exposes a cancellation contract, but the current Streamlit interface cannot interrupt an in-flight request from a second browser event.
- A 60-second client timeout bounds stalled requests. Slow models may require a future user-configurable local setting.
- Partial streamed output is retained in the session when the connection fails.
- Model quality, safety, licensing, context size, and hardware needs depend on the model selected in Ollama.
- Saved conversations, remote endpoints, cloud models, tool calling, and public hosting are intentionally out of scope.
