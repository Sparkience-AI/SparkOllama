from pathlib import Path


def test_ui_never_enables_unsafe_html_for_conversation_content() -> None:
    source = (Path(__file__).parents[1] / "src" / "sparkollama" / "ui.py").read_text(
        encoding="utf-8"
    )

    assert "unsafe_allow_html=True" not in source
    assert "unsafe_allow_html=False" in source
