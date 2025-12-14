from __future__ import annotations

import sys
from contextlib import nullcontext
from typing import ContextManager

from rich.console import Console


def build_console(use_rich: bool) -> Console:
    return Console(file=sys.stderr, force_terminal=use_rich, stderr=True)


def status(console: Console, enabled: bool, message: str) -> ContextManager:
    if enabled:
        return console.status(message, spinner="dots")
    return nullcontext()
