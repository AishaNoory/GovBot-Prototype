import pytest

from app.utils.pii import detect_pii, redact_pii


def test_detect_email():
    text = "Contact me at user@example.com for details."
    matches = detect_pii(text)
    kinds = {m.kind for m in matches}
    assert "email" in kinds


def test_detect_phone():
    text = "+254712345678 and 0712345678 and 0112345678"
    matches = detect_pii(text)
    kinds = {m.kind for m in matches}
    assert "phone" in kinds


def test_redact():
    text = "ID 12345678, phone 0712345678, email user@example.com"
    matches = detect_pii(text)
    red = redact_pii(text, matches)
    assert "12345678" not in red
    assert "0712345678" not in red
    assert "user@example.com" not in red
    assert "<EMAIL_REDACTED>" in red
    assert "<PHONE_REDACTED>" in red
    assert "<NATIONAL_ID_REDACTED>" in red
