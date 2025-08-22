#!/usr/bin/env python3
"""
Test script to verify Windows compatibility changes.
"""

import platform
from agent.utils import get_os_name, format_system_context, get_subprocess_kwargs, get_shell_prompt
from interface.shell_interface import clear_screen


def test_windows_compatibility():
    """Test all Windows compatibility functions."""
    print("=== Testing Windows Compatibility ===\n")

    # Test OS detection
    print("1. OS Detection:")
    print(f"   get_os_name(): {get_os_name()}")
    print(f"   platform.system(): {platform.system()}")
    print()

    # Test system context
    print("2. System Context:")
    context = format_system_context()
    print(context)
    print()

    # Test subprocess kwargs
    print("3. Subprocess Configuration:")
    kwargs = get_subprocess_kwargs()
    print(f"   subprocess kwargs: {kwargs}")
    print()

    # Test shell prompt
    print("4. Shell Prompt:")
    prompt = get_shell_prompt(agent_mode=True)
    print(f"   Prompt: {repr(prompt)}")
    print()

    # Test clear screen function (just check it exists)
    print("5. Clear Screen Function:")
    print(f"   clear_screen function exists: {callable(clear_screen)}")
    print()

    print("=== Test Complete ===")


if __name__ == "__main__":
    test_windows_compatibility()
