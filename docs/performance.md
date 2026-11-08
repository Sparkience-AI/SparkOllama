# Performance envelope

- Prompt: at most 8,000 characters.
- Provider context: at most 25 messages and 32,000 characters.
- Response: at most 16,000 characters in application and MCP aggregation.
- MCP model listing: at most 100 entries, with model names limited to 200 characters.
- Ollama request timeout: 60 seconds by default; model startup may still dominate first-token latency.
- MCP concurrency: one synchronous request per tool call; no background jobs or persistent sessions.
- MCP generation accepts only an exact model name already reported by the local Ollama service.

Model memory, disk, and latency depend on the chosen Ollama model and are outside SparkOllama's guarantees. CI uses fake providers and asserts deterministic bounds; release review should smoke-test one documented small model on a clean source checkout.
