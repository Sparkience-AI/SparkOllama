# Threat model

SparkOllama is a local application, not an isolation boundary. Protected assets are prompt text, BYOK credentials, model output, and control of the local Ollama service.

Primary threats are a remotely exposed Ollama daemon, prompt injection in user-supplied text, credential disclosure, oversized responses, malicious model output, dependency compromise, and clients misrepresenting MCP capabilities. Controls include loopback-only endpoints, session-owned keys, explicit cloud consent, bounded context/output, escaped UI rendering, sanitized errors, pinned build actions, and a stdio MCP with three fixed local-only tools.

The MCP never exposes cloud providers, files, browsing, model installation, shell access, persistence, or external actions. Stdio transport inherits the launching user's permissions; only trusted local clients should launch it. Model output remains untrusted and must not be treated as instructions or verified facts.

Residual risks include Ollama/model vulnerabilities, other local processes reading memory, dependency compromise, and denial of service within configured time/resource bounds.
