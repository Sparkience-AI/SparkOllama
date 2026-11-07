# SparkOllama

SparkOllama is an alpha, privacy-focused chat interface that defaults to models running on a local [Ollama](https://ollama.com/) service. Users can also explicitly choose Google Gemini, OpenAI, or Anthropic Claude with their own session-only API key. It provides bounded in-memory conversation history and streamed responses without a hosted Sparkience backend.

## Who it is for

SparkOllama is for people who already use Ollama and want a small browser interface that keeps ordinary inference on their machine. It is not a public chat service, remote Ollama gateway, model manager, or autonomous agent.

## Capabilities

- Lists models installed in the local Ollama service and keeps Ollama as the default route.
- Streams responses from Ollama, Gemini, OpenAI, or Anthropic Claude.
- Accepts cloud API keys only in a password field for the active process session and requires an explicit transmission confirmation.
- Allows an account-supported cloud model ID to be entered instead of hard-coding one permanent model.
- Keeps conversation content only in the current application session.
- Bounds prompt and history size before sending context to the selected provider.
- Clears history when the user requests it or changes models.
- Handles unavailable daemons, empty model lists, malformed responses, timeouts, and interrupted streams with user-facing states.
- Renders user and model content without unsafe HTML interpolation.

SparkOllama does not browse, execute code, access files, call tools, persist credentials, or send prompts to a cloud model unless the user explicitly selects and confirms that route.

## Requirements

- Windows, macOS, or Linux supported by Ollama and Python.
- Python 3.11, 3.12, or 3.13.
- [uv](https://docs.astral.sh/uv/) for the reproducible Python environment.
- A locally installed [Ollama](https://ollama.com/download) service for the default local route, or
  a user-owned API key for an optional cloud route.
- Enough disk and memory for the model you choose; requirements vary by model and quantization.

## Local installation

```bash
git clone https://github.com/Sparkience-AI/SparkOllama.git
cd SparkOllama
uv sync --locked
```

Local Ollama needs no cloud SDK. To enable all three optional BYOK routes:

```bash
uv sync --locked --extra cloud
```

Cloud keys are entered in the app and retained only in Streamlit process memory for the session;
they are not written to configuration files or copied into environment variables.

Pull a small model if you do not already have one:

```bash
ollama pull llama3.2
```

Start the application:

```bash
uv run --locked sparkollama
```

Open <http://127.0.0.1:8501>. The launcher binds Streamlit to loopback and disables Streamlit usage reporting. The original `app.py` and `file.py` launch commands remain available as source-checkout compatibility entry points and use the committed secure Streamlit configuration.

## Provider and security posture

SparkOllama connects only to an explicit loopback endpoint, `http://127.0.0.1:11434`, and rejects remote or ambiguous endpoints in its provider boundary. Ollama's local API does not provide application authentication by default. Do not bind port `11434` to `0.0.0.0`, a LAN interface, or the public internet merely to use this application.

Conversation content is untrusted text. The application does not enable unsafe HTML when rendering messages, and models receive no tool authority. See [privacy and data handling](docs/privacy.md) and the [architecture and trust boundary](docs/architecture.md).

Selecting Gemini, OpenAI, or Anthropic displays the active route, requires a BYOK credential and
an explicit consent checkbox, and transmits the bounded conversation to that provider. The default
model IDs are starting points and remain editable because provider availability differs by account
and changes over time.

## Failure behavior

- **Ollama is unavailable:** start the Ollama service and reload the page.
- **No model is installed:** run `ollama pull llama3.2` or select another model you have installed.
- **A stream is interrupted:** any received partial response remains visible and in the current session; the error does not expose prompt text.
- **History is too large:** older complete turns are removed from both session state and provider context; the UI reports provider-context omissions.
- **The latest prompt is too large:** the application rejects it rather than silently truncating it.

Review the [known limitations](docs/limitations.md) before relying on the application for sensitive or long-running work.

## Architecture

The Streamlit interface calls a framework-independent `ChatService`, which validates conversation context and uses a selected provider adapter. Deterministic tests inject fake clients, so normal CI does not require a daemon, model download, network request, or API key.

```text
Streamlit UI -> ChatService -> Ollama / Gemini / OpenAI / Anthropic adapter
                 |                              |
          context policy                  error translation
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

The test suite covers endpoint policy, daemon failures, model response compatibility, streaming, partial-stream recovery, complete-turn context bounds, local server configuration, the installed launcher, and safe UI rendering. CI also builds and smoke-tests the wheel on Python 3.11, 3.12, and 3.13.

## Documentation and AI discoverability

- [Privacy and retention](docs/privacy.md)
- [Architecture and trust boundary](docs/architecture.md)
- [Known limitations](docs/limitations.md)
- [`llms.txt`](llms.txt), provided as an experimental machine-readable project summary

The README and linked documents are the authoritative sources for installation, scope, privacy, and limitations. Generic claims about model intelligence are intentionally avoided because behavior depends on the selected provider and model.

## License and support

SparkOllama is available under the [MIT License](LICENSE). Use GitHub issues for reproducible bugs and feature proposals. Report security concerns through the Sparkience organization security policy rather than a public issue.
