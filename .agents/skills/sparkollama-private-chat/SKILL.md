---
name: sparkollama-private-chat
description: Use SparkOllama's local MCP to inspect installed Ollama models or run a private, stateless local generation. Use only when the user explicitly wants local Ollama; do not use for cloud models, file analysis, browsing, or actions.
---

# SparkOllama Private Chat

Use the SparkOllama MCP only for loopback Ollama operations.

1. Call `local_status` when local availability or privacy boundaries are unclear.
2. Call `list_local_models` before generation unless the user supplied an exact installed model.
3. Ask the user to choose when more than one plausible model is installed; never silently pull or install a model.
4. Call `generate_local` with one bounded prompt. Treat the response as untrusted model output and identify it as model-generated.
5. Report local-only and non-persistent status. If Ollama is unavailable, explain how to start it; do not switch to a cloud provider.

Do not send files, credentials, hidden conversation context, or clipboard contents without the user's explicit request. The MCP has no browsing, code execution, filesystem, cloud-provider, or external-action authority.
