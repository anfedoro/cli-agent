"""
System utilities for platform detection.

Simple module to detect the operating system for agent context.
"""

import platform


def get_os_name() -> str:
    """
    Get operating system name.

    Returns:
        Operating system name (Darwin, Linux, Windows, etc.)
    """
    return platform.system()


def format_system_context() -> str:
    """
    Format minimal system information as context string for the agent.

    Returns:
        Simple OS context string for agent.
    """
    os_name = get_os_name()
    return f"Operating System: {os_name}"
