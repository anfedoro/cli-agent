"""
Simple input handler with readline support for session history and editing.

Just imports readline to enable enhanced input() functionality.
"""

# Global flag to track readline availability
_readline_available = False

try:
    import readline

    # Configure readline when imported
    readline.set_history_length(1000)
    readline.parse_and_bind("tab: complete")
    readline.parse_and_bind("set editing-mode emacs")

    _readline_available = True

except ImportError:
    # readline not available (Windows)
    _readline_available = False


def enhanced_input(prompt: str = "") -> str:
    """Get user input. Uses readline automatically if available."""
    return input(prompt)


def cleanup_input_handler():
    """Cleanup function for compatibility."""
    pass


def is_readline_available() -> bool:
    """Check if readline is available."""
    return _readline_available
