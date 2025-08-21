"""
Enhanced input handler with readline support for session history, editing, and path completion.

This module attempts to use the readline library for better input handling,
including command history, line editing, and path auto-completion.
Falls back gracefully to basic input() if readline is not available.
"""

import os
import glob
import atexit
from typing import Optional

# Global flag to track readline availability
_readline_available = False

try:
    # Try importing readline
    import readline
    from agent.config import get_history_file

    def setup_readline():
        """Setup readline with history support."""
        history_file = get_history_file()

        # Load existing history
        try:
            if history_file.exists():
                readline.read_history_file(str(history_file))
        except (FileNotFoundError, PermissionError, OSError):
            pass  # History file doesn't exist, can't be read, or other OS error

        # Save history on exit
        def save_history():
            try:
                readline.write_history_file(str(history_file))
            except (FileNotFoundError, PermissionError, OSError):
                pass  # Can't save history file

        atexit.register(save_history)

    def path_completer(text: str, state: int) -> Optional[str]:
        """Universal path completion function that works in any context."""
        try:
            # Simple approach: just complete the text as given
            if not text:
                text = "./"

            # Handle paths with spaces and special characters
            if text.startswith(("~", "/")):
                # Absolute path or home directory
                expanded_text = os.path.expanduser(text)
                pattern = expanded_text + "*"
            else:
                # Relative path
                pattern = text + "*"

            matches = []
            for path in glob.glob(pattern):
                # Make path relative if original text was relative
                if not text.startswith(("~", "/")):
                    path = os.path.relpath(path)

                # Add trailing slash for directories
                if os.path.isdir(path):
                    path += "/"

                matches.append(path)

            # Sort matches for consistent ordering
            matches.sort()

            return matches[state] if state < len(matches) else None

        except (OSError, ValueError, IndexError):
            return None

    # Configure readline - detect if using libedit (macOS) or GNU readline
    readline.set_history_length(1000)
    readline.set_completer(path_completer)

    # Check if we're using libedit (macOS default)
    if "libedit" in getattr(readline, "__doc__", "").lower():
        # macOS libedit configuration
        readline.parse_and_bind("bind ^I rl_complete")  # Bind Tab to completion
    else:
        # GNU readline configuration
        readline.parse_and_bind("tab: complete")
        readline.parse_and_bind("set editing-mode emacs")

    # Set word delimiters (works for both)
    readline.set_completer_delims(" \t\n")

    # Setup history support
    setup_readline()

    _readline_available = True

except ImportError:
    # readline not available (Windows without pyreadline3)
    _readline_available = False


def enhanced_input(prompt: str = "") -> str:
    """Get user input. Uses readline automatically if available."""
    return input(prompt)


def cleanup_input_handler():
    """Cleanup function for compatibility."""
    if _readline_available:
        try:
            from agent.config import get_history_file

            history_file = get_history_file()
            readline.write_history_file(str(history_file))
        except (NameError, ImportError, FileNotFoundError, PermissionError, OSError):
            pass  # Can't save history


def is_readline_available() -> bool:
    """Check if readline is available."""
    return _readline_available
