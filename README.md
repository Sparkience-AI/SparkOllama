# SparkOllama

SparkOllama is an alpha, privacy-focused chat interface for models running on a local [Ollama](https://ollama.com/) service. It provides model discovery, bounded in-memory conversation history, and streamed responses without adding a cloud provider or hosted backend.

## Who it is for

SparkOllama is for people who already use Ollama and want a small browser interface that keeps ordinary inference on their machine. It is not a public chat service, remote Ollama gateway, model manager, or autonomous agent.

## Capabilities

- Lists models installed in the local Ollama service.
- Streams local model responses into a Streamlit chat interface.
- Keeps conversation content only in the current application session.
- Bounds prompt and history size before sending context to Ollama.
- Clears history when the user requests it or changes models.
- Handles unavailable daemons, empty model lists, malformed responses, timeouts, and interrupted streams with user-facing states.
- Renders user and model content without unsafe HTML interpolation.

SparkOllama does not browse, execute code, access files, call tools, or send prompts to a cloud model.

## Requirements

- Windows, macOS, or Linux supported by Ollama and Python.
- Python 3.11, 3.12, or 3.13.
- [uv](https://docs.astral.sh/uv/) for the reproducible Python environment.
- A locally installed [Ollama](https://ollama.com/download) service.
- Enough disk and memory for the model you choose; requirements vary by model and quantization.

## Local installation

```bash
git clone https://github.com/Sparkience-AI/SparkOllama.git
cd SparkOllama
uv sync --locked
```

Pull a small model if you do not already have one:

```bash
ollama pull llama3.2
```

Start the application:

```bash
uv run --locked streamlit run app.py
```

Open <http://localhost:8501>. The original `file.py` launch command remains available as a compatibility entry point.

## Local security posture

SparkOllama connects only to an explicit loopback endpoint, `http://127.0.0.1:11434`, and rejects remote or ambiguous endpoints in its provider boundary. Ollama's local API does not provide application authentication by default. Do not bind port `11434` to `0.0.0.0`, a LAN interface, or the public internet merely to use this application.

Conversation content is untrusted text. The application does not enable unsafe HTML when rendering messages, and models receive no tool authority. See [privacy and data handling](docs/privacy.md) and the [architecture and trust boundary](docs/architecture.md).

## Failure behavior

- **Ollama is unavailable:** start the Ollama service and reload the page.
- **No model is installed:** run `ollama pull llama3.2` or select another model you have installed.
- **A stream is interrupted:** any received partial response remains visible and in the current session; the error does not expose prompt text.
- **History is too large:** older complete messages are omitted from the provider context and the UI reports the count.
- **The latest prompt is too large:** the application rejects it rather than silently truncating it.

Review the [known limitations](docs/limitations.md) before relying on the application for sensitive or long-running work.

## Architecture

The Streamlit interface calls a framework-independent `ChatService`, which validates conversation context and uses an `OllamaProvider` adapter. Deterministic tests inject fake clients, so normal CI does not require a daemon, model download, network request, or API key.

```text
Streamlit UI -> ChatService -> loopback-only OllamaProvider -> local Ollama daemon
                 |                         |
          context policy             error translation
```

## Development

Run the same checks used by CI:

```bash
uv sync --locked --all-groups
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked mypy src
uv run --locked pytest -q
uv build --no-sources
```

The test suite covers endpoint policy, daemon failures, model response compatibility, streaming, cancellation, partial-stream recovery, context bounds, and safe UI rendering.

## Documentation and AI discoverability

- [Privacy and retention](docs/privacy.md)
- [Architecture and trust boundary](docs/architecture.md)
- [Known limitations](docs/limitations.md)
- [`llms.txt`](llms.txt), provided as an experimental machine-readable project summary

The README and linked documents are the authoritative sources for installation, scope, privacy, and limitations. Generic claims about model intelligence are intentionally avoided because behavior depends on the selected local model.

## License and support

SparkOllama is available under the [MIT License](LICENSE). Use GitHub issues for reproducible bugs and feature proposals. Report security concerns through the Sparkience organization security policy rather than a public issue.
