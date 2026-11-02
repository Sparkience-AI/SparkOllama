# Privacy and data handling

SparkOllama is designed for a local Ollama service on `127.0.0.1` or `localhost`.

- Prompts and model responses remain in the active Streamlit session and are not saved by SparkOllama.
- Clearing the chat removes the current in-memory application history.
- SparkOllama disables Streamlit usage reporting and has no application telemetry, user accounts, cloud provider, or analytics integration.
- Ollama model downloads require network access, but ordinary inference is local after the model is present.
- Local models and Ollama may have their own files, caches, and logs. Review Ollama's configuration when local retention matters.

The committed configuration and installed launcher bind the Streamlit interface to `127.0.0.1`. SparkOllama does not treat a browser-accessible Ollama endpoint as authenticated. Keep ports `8501` and `11434` bound to loopback. Do not expose either service on a LAN or the public internet without a separately designed authenticated and encrypted gateway.
