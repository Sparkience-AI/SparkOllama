# Current limitations

SparkOllama is an alpha local chat client, not a hosted service.

- Only a loopback Ollama service is supported.
- Conversation history exists only in the current Streamlit session.
- Context is bounded by message and character limits, not a model-specific tokenizer.
- The current Streamlit interface cannot cancel an in-flight request. A 60-second Ollama client timeout bounds stalled requests; slow models may require a future user-configurable local setting.
- Partial streamed output is retained in the session when the connection fails.
- Model quality, safety, licensing, context size, and hardware needs depend on the model selected in Ollama.
- Saved conversations, remote endpoints, cloud models, tool calling, and public hosting are intentionally out of scope.
