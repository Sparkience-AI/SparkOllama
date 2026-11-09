from collections.abc import Iterator

import pytest

from sparkollama.service import managed_stream
from sparkollama.session import credential_fingerprint


class ClosableStream(Iterator[str]):
    def __init__(self) -> None:
        self.closed = False
        self._chunks = iter(("first", "second"))

    def __next__(self) -> str:
        return next(self._chunks)

    def close(self) -> None:
        self.closed = True


def test_credential_identity_is_stable_only_within_one_salted_session() -> None:
    first_salt = b"a" * 32
    second_salt = b"b" * 32
    first = credential_fingerprint("account-one-key", first_salt)

    assert first == credential_fingerprint("account-one-key", first_salt)
    assert first != credential_fingerprint("account-two-key", first_salt)
    assert first != credential_fingerprint("account-one-key", second_salt)
    assert "account-one-key" not in first


def test_credential_identity_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        credential_fingerprint("", b"a" * 32)
    with pytest.raises(ValueError, match="at least 16"):
        credential_fingerprint("key", b"short")


def test_managed_stream_closes_after_early_stop() -> None:
    stream = ClosableStream()

    with managed_stream(stream) as active:
        assert next(active) == "first"

    assert stream.closed is True


def test_managed_stream_closes_after_consumer_error() -> None:
    stream = ClosableStream()

    with pytest.raises(RuntimeError, match="consumer stopped"):
        with managed_stream(stream):
            raise RuntimeError("consumer stopped")

    assert stream.closed is True
