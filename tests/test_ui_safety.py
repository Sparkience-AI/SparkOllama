import tomllib
from pathlib import Path


def test_ui_never_enables_unsafe_html_for_conversation_content() -> None:
    source = (Path(__file__).parents[1] / "src" / "sparkollama" / "ui.py").read_text(
        encoding="utf-8"
    )

    assert "unsafe_allow_html=True" not in source
    assert "unsafe_allow_html=False" in source


def test_cloud_routes_require_password_input_and_explicit_consent() -> None:
    source = (Path(__file__).parents[1] / "src" / "sparkollama" / "ui.py").read_text(
        encoding="utf-8"
    )

    assert 'type="password"' in source
    assert "confirm cloud transmission" in source
    assert "credential_fingerprint" in source
    assert "api_key}" not in source
    assert '"Google Gemini"' in source
    assert '"OpenAI"' in source
    assert '"Anthropic Claude"' in source
    assert "os.environ" not in source


def test_ui_manages_provider_stream_cleanup() -> None:
    source = (Path(__file__).parents[1] / "src" / "sparkollama" / "ui.py").read_text(
        encoding="utf-8"
    )

    assert "with managed_stream(stream):" in source


def test_streamlit_is_loopback_only_and_usage_reporting_is_disabled() -> None:
    config_path = Path(__file__).parents[1] / ".streamlit" / "config.toml"
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))

    assert config["server"]["address"] == "127.0.0.1"
    assert config["browser"]["gatherUsageStats"] is False
