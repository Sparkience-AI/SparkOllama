# Release checklist

1. Confirm the tag matches `pyproject.toml` and update the changelog/release notes.
2. Run locked tests, formatting, lint, strict typing, wheel/sdist build, and installed-entry-point smoke tests on Python 3.11–3.13.
3. Test source-run Streamlit and stdio MCP startup with local Ollama; cloud tests use fake clients unless a maintainer explicitly approves a live-key smoke test.
4. Review privacy, threat model, limitations, performance envelope, skill routing evals, and accessibility labels/keyboard behavior.
5. Run the release-evidence workflow and attach the wheel, source archive, SHA-256 file, CycloneDX SBOM, and provenance manifest.
6. Verify installation from the wheel in a clean virtual environment and document known limitations and rollback to the previous tag.

This checklist covers source archives and Python wheels only; hosted-service releases are out of scope.
