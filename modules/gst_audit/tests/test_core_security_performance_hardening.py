from __future__ import annotations

import logging
import sys
from decimal import Decimal

import pytest

from app.core import security
from app.core.logging_config import setup_logging
from app.core.money import format_inr_compact, money_float, to_decimal
from app.core.performance import ProcessingStats, current_memory_mb


def test_security_permissions_and_invalid_roles_are_explicit() -> None:
    assert security.has_permission(security.Role.ADMIN, security.Permission.MANAGE_USERS)
    assert security.has_permission("AUDITOR", "EXPORT_REPORTS")
    assert not security.has_permission(security.Role.VIEWER, security.Permission.EXPORT_REPORTS)
    with pytest.raises(ValueError):
        security.has_permission("UNKNOWN", "EXPORT_REPORTS")
    with pytest.raises(ValueError):
        security.has_permission("VIEWER", "UNKNOWN_PERMISSION")


def test_security_hashing_event_chain_and_constant_time_compare(tmp_path) -> None:
    source = tmp_path / "sample.txt"
    source.write_text("audit payload", encoding="utf-8")
    file_hash = security.sha256_file(source)
    assert len(file_hash) == 64
    assert security.canonical_payload_hash({"b": 2, "a": 1}) == security.canonical_payload_hash({"a": 1, "b": 2})

    first = security.create_security_event("IMPORT", "auditor", "file", {"hash": file_hash})
    second = security.create_security_event("REVIEW", "reviewer", "row-1", ["accepted"], previous_hash=first.event_hash)
    assert second.previous_hash == first.event_hash
    assert security.constant_time_hash_equal(first.event_hash, first.event_hash)
    assert not security.constant_time_hash_equal(first.event_hash, second.event_hash)


def test_security_encrypt_decrypt_bytes_and_files(tmp_path) -> None:
    salt = b"1234567890abcdef"
    encrypted = security.encrypt_bytes(b"secret gst data", "strong-password", salt=salt)
    assert encrypted.startswith(b"GSTAP1" + salt)
    assert security.decrypt_bytes(encrypted, "strong-password") == b"secret gst data"
    with pytest.raises(ValueError):
        security.decrypt_bytes(encrypted, "wrong-password")
    with pytest.raises(ValueError):
        security.encrypt_bytes(b"x", "")
    with pytest.raises(ValueError):
        security.decrypt_bytes(b"bad", "strong-password")

    source = tmp_path / "plain.bin"
    encrypted_path = tmp_path / "plain.enc"
    decrypted_path = tmp_path / "plain.out"
    source.write_bytes(b"file secret")
    assert security.encrypt_file(source, encrypted_path, "pw") == encrypted_path
    assert security.decrypt_file(encrypted_path, decrypted_path, "pw") == decrypted_path
    assert decrypted_path.read_bytes() == b"file secret"


def test_performance_stats_and_fallback_memory(monkeypatch) -> None:
    stats = ProcessingStats.start()
    stats.rows_processed = 250
    message = stats.progress_message("Reading")
    assert "Reading" in message
    assert "rows: 250" in message
    assert stats.rows_per_second >= 0
    assert stats.elapsed_seconds >= 0.001

    monkeypatch.setitem(sys.modules, "psutil", None)
    assert current_memory_mb() >= 0


def test_logging_setup_creates_file_and_is_idempotent(tmp_path) -> None:
    root = logging.getLogger()
    old_handlers = list(root.handlers)
    for handler in old_handlers:
        root.removeHandler(handler)
    try:
        log_file = tmp_path / "logs" / "audit.log"
        assert setup_logging(log_file) == log_file
        assert log_file.parent.exists()
        assert setup_logging(log_file) == log_file
    finally:
        for handler in list(root.handlers):
            handler.close()
            root.removeHandler(handler)
        for handler in old_handlers:
            root.addHandler(handler)


def test_money_edge_cases_and_compact_formats() -> None:
    assert to_decimal(None) == Decimal("0.00")
    assert to_decimal(float("nan")) == Decimal("0.00")
    assert to_decimal("₹ 12,345.678 text") == Decimal("12345.68")
    assert money_float("₹99.10") == pytest.approx(99.10)
    assert format_inr_compact(19_380_000) == "₹1.94Cr"
    assert format_inr_compact(-250_000) == "-₹2.50L"
    assert format_inr_compact(9_999) == "₹10.0K"
