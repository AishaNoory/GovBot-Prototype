"""
Basic PII detection and redaction utilities.

This module provides lightweight regex-based detectors for common PII patterns
so we can warn users and avoid storing/echoing sensitive data.

Note: This is a heuristic pre-filter and not a substitute for a
full DLP solution. Prefer server-side validation and progressive enhancement.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Pattern, Tuple


@dataclass
class PIIMatch:
    kind: str
    match: str
    start: int
    end: int


def _compile_patterns() -> Dict[str, Pattern[str]]:
    """Compile regex patterns for PII detection.

    Patterns are intentionally conservative to reduce false positives.
    """
    return {
        # Basic email
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        # Kenyan phone formats (e.g., +2547XXXXXXXX, 07XXXXXXXX, 01XXXXXXXX)
        "phone": re.compile(r"\b(?:\+?254|0)(?:7|1)\d{8}\b"),
        # National ID: commonly 7 or 8 digits (heuristic)
        "national_id": re.compile(r"\b\d{7,8}\b"),
        # Passport: alphanumeric 6-9 chars (heuristic)
        "passport": re.compile(r"\b[A-Za-z0-9]{6,9}\b"),
    }


_PATTERNS = _compile_patterns()


def detect_pii(text: str) -> List[PIIMatch]:
    """Detect likely PII in text and return a list of matches.

    Args:
        text: Input text to scan.

    Returns:
        List of PIIMatch entries describing potential PII spans.
    """
    if not text:
        return []

    matches: List[PIIMatch] = []
    for kind, pattern in _PATTERNS.items():
        for m in pattern.finditer(text):
            # Basic filtering to reduce excessive false positives for generic numeric tokens
            if kind in {"national_id", "passport"}:
                # Skip if the token is part of a URL or email already captured
                surrounding = text[max(0, m.start()-8): m.end()+8]
                if "http" in surrounding or "@" in surrounding:
                    continue
            matches.append(PIIMatch(kind=kind, match=m.group(0), start=m.start(), end=m.end()))
    return matches


def redact_pii(text: str, matches: Optional[List[PIIMatch]] = None) -> str:
    """Redact detected PII spans in the text using kind-specific placeholders.

    Args:
        text: Input text
        matches: Optional precomputed matches

    Returns:
        Redacted string
    """
    if not text:
        return text
    matches = matches if matches is not None else detect_pii(text)
    if not matches:
        return text

    # Replace from end to start to keep offsets stable
    redacted = text
    for m in sorted(matches, key=lambda x: x.start, reverse=True):
        placeholder = f"<{m.kind.upper()}_REDACTED>"
        redacted = redacted[: m.start] + placeholder + redacted[m.end :]
    return redacted
