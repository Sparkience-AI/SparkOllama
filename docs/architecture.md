# Architecture

SparkOllama has four small boundaries:

1. `app.py` and `file.py` launch the Streamlit interface.
2. `sparkollama.ui` owns display and session state but not Ollama protocol handling.
3. `sparkollama.service` validates and bounds conversation context.
4. `sparkollama.providers` enforces the loopback endpoint policy and translates Ollama responses and failures.

The UI and deterministic tests use the same typed service contracts. Standard tests use fake clients and do not require a running daemon or model download.

## Trust boundary

User and model messages are untrusted text. They are rendered through Streamlit without enabling unsafe HTML. The only supported provider endpoint is an explicit loopback HTTP(S) URL with no credentials, query, fragment, or API path.

SparkOllama does not give the model tools, filesystem access, browsing, code execution, or permission to perform external actions.
