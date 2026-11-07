from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.release_evidence import build_evidence


def test_release_evidence_contains_artifact_hash_sbom_and_revision(
    tmp_path: Path, monkeypatch
) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = dist / "sparkollama-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    monkeypatch.setenv("GITHUB_SHA", "abc123")
    output = tmp_path / "evidence"
    build_evidence(dist, output, "sparkollama", "0.1.0")
    checksums = json.loads((output / "SHA256SUMS.json").read_text(encoding="utf-8"))
    assert checksums[wheel.name] == hashlib.sha256(b"wheel").hexdigest()
    assert json.loads((output / "sbom.cdx.json").read_text())["bomFormat"] == "CycloneDX"
    assert json.loads((output / "provenance.json").read_text())["source_revision"] == "abc123"
