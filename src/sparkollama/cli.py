"""Installed SparkOllama launcher."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from sparkollama import __version__


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local SparkOllama interface.")
    parser.add_argument("--version", action="version", version=f"SparkOllama {__version__}")
    parser.add_argument("--port", type=int, default=8501, help="Loopback Streamlit port.")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65_535:
        parser.error("--port must be between 1 and 65535")

    ui_path = Path(__file__).with_name("ui.py")
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(ui_path),
            "--server.address=127.0.0.1",
            "--browser.gatherUsageStats=false",
            f"--server.port={args.port}",
        ]
    )
