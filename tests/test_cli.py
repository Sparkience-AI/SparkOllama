from __future__ import annotations

from collections.abc import Sequence

from sparkollama import cli


def test_cli_launches_streamlit_with_local_security_flags(monkeypatch) -> None:
    command: Sequence[str] = []

    def fake_call(args: Sequence[str]) -> int:
        nonlocal command
        command = args
        return 0

    monkeypatch.setattr(cli.subprocess, "call", fake_call)

    assert cli.main(["--port", "8765"]) == 0
    assert "--server.address=127.0.0.1" in command
    assert "--browser.gatherUsageStats=false" in command
    assert "--server.port=8765" in command
