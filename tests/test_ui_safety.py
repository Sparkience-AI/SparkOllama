import tomllib
from pathlib import Path


def test_ui_never_enables_unsafe_html_for_conversation_content() -> None:
    source = (Path(__file__).parents[1] / "src" / "sparkollama" / "ui.py").read_text(
        encoding="utf-8"
    )

    assert "unsafe_allow_html=True" not in source
    assert "unsafe_allow_html=False" in source


def test_streamlit_is_loopback_only_and_usage_reporting_is_disabled() -> None:
    config_path = Path(__file__).parents[1] / ".streamlit" / "config.toml"
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))

    assert config["server"]["address"] == "127.0.0.1"
    assert config["browser"]["gatherUsageStats"] is False
