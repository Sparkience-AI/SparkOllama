"""Local stdio MCP entry point for bounded SparkOllama operations."""

from __future__ import annotations

from typing import Any

from sparkollama.mcp_tools import generate_local, list_local_models, local_status


def build_server() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - exercised by installed-extra smoke tests
        raise RuntimeError("Install the agent extra with `uv sync --extra agent`.") from exc

    server = FastMCP(
        "sparkollama",
        instructions=(
            "Local-only Ollama diagnostics and stateless generation. "
            "Never claim cloud-provider access, persistence, browsing, or tool execution."
        ),
    )

    @server.tool(name="local_status")  # type: ignore[untyped-decorator]
    def status_tool() -> dict[str, object]:
        """Describe this server's local-only, non-persistent boundary."""

        return local_status()

    @server.tool(name="list_local_models")  # type: ignore[untyped-decorator]
    def models_tool() -> dict[str, object]:
        """List models installed in the loopback Ollama service."""

        return list_local_models()

    @server.tool(name="generate_local")  # type: ignore[untyped-decorator]
    def generation_tool(model: str, prompt: str) -> dict[str, object]:
        """Run one bounded, stateless prompt against an installed local model."""

        return generate_local(model, prompt)

    return server


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
