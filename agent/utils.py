from __future__ import annotations


def is_reset_command(text: str | None) -> bool:
    """Return True when the input requests a reset (/reset or reset)."""
    if not text:
        return False
    normalized = text.strip().lower()
    return normalized in ("reset", "/reset")
