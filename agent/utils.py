"""
System utilities for platform detection and shell integration.

Simple module to detect the operating system for agent context
and provide shell-related utilities.
"""

import os
import platform
import getpass
import socket
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import re


def get_os_name() -> str:
    """
    Get operating system name.

    Returns:
        Operating system name (Darwin, Linux, Windows, etc.)
    """
    return platform.system()


def get_subprocess_kwargs() -> Dict[str, Any]:
    """
    Get appropriate subprocess kwargs for the current platform.

    Returns:
        dict: kwargs for subprocess.run() including shell settings
    """
    kwargs: Dict[str, Any] = {"shell": True, "capture_output": True, "text": True}

    # On Windows, try to use PowerShell if available
    if platform.system() == "Windows":
        pwsh_path = shutil.which("pwsh")
        if pwsh_path:
            kwargs["executable"] = pwsh_path
        else:
            powershell_path = shutil.which("powershell")
            if powershell_path:
                kwargs["executable"] = powershell_path
        # If neither PowerShell is available, use default CMD (no executable specified)

    return kwargs


def _get_timeout_env_var(name: str) -> Optional[int]:
    """Helper to parse integer timeout from environment; returns None if unset/invalid/<=0."""
    val = os.getenv(name)
    if not val:
        return None
    try:
        num = int(val)
        return num if num > 0 else None
    except Exception:
        return None


def get_timeout_seconds(kind: str = "shell") -> Optional[int]:
    """Get timeout in seconds for command execution.

    Precedence: ENV overrides settings. If nothing is configured, apply
    sensible defaults to prevent indefinite hangs.
    - kind: "shell" or "tool"
    ENV: CLI_AGENT_SHELL_TIMEOUT / CLI_AGENT_TOOL_TIMEOUT
    Settings: shell_command_timeout_seconds / tool_command_timeout_seconds
    Defaults: shell=300s (5 min), tool=120s (2 min)
    """
    from agent.config import get_setting

    if kind == "tool":
        env_timeout = _get_timeout_env_var("CLI_AGENT_TOOL_TIMEOUT")
        if env_timeout is not None:
            return env_timeout
        setting = get_setting("tool_command_timeout_seconds", None)
        # Default to 120s for tools if unset
        if setting is None:
            return 120
    else:
        env_timeout = _get_timeout_env_var("CLI_AGENT_SHELL_TIMEOUT")
        if env_timeout is not None:
            return env_timeout
        setting = get_setting("shell_command_timeout_seconds", None)
        # Default to 300s (5 minutes) for shell if unset
        if setting is None:
            return 300

    try:
        if setting is None:
            return None  # Should not happen due to defaults above
        val = int(setting)
        return val if val > 0 else None
    except Exception:
        return None


def _get_llm_timeout_env_var() -> Optional[int]:
    """Parse LLM timeout from environment variable CLI_AGENT_LLM_TIMEOUT."""
    return _get_timeout_env_var("CLI_AGENT_LLM_TIMEOUT")


def get_llm_timeout_seconds() -> Optional[int]:
    """Get HTTP timeout (seconds) for LLM API requests.

    Precedence: ENV overrides settings. Defaults to 120s if unset.
    - ENV: CLI_AGENT_LLM_TIMEOUT
    - Settings: llm_request_timeout_seconds
    - Default: 120 seconds
    """
    from agent.config import get_setting

    env_timeout = _get_llm_timeout_env_var()
    if env_timeout is not None:
        return env_timeout

    setting = get_setting("llm_request_timeout_seconds", None)
    if setting is None:
        return 120

    try:
        val = int(setting)
        return val if val > 0 else None
    except Exception:
        return 120


def should_run_interactive(command: str, program: Optional[str] = None) -> bool:
    """Heuristically decide whether to run command attached to TTY.

    - Known TUI programs (ncdu, top, htop, btop, less, more, vim, nvim, nano, ranger, mc, fzf, watch, man, tmux, screen)
    - Piped into less/more
    - "tail -f" like follow modes
    """
    cmd = command.strip()
    prog = (program or (cmd.split()[0] if cmd else "")).lower()

    known_tui = {
        "ncdu",
        "top",
        "htop",
        "btop",
        "less",
        "more",
        "vim",
        "nvim",
        "nano",
        "ranger",
        "mc",
        "fzf",
        "watch",
        "man",
        "tmux",
        "screen",
    }

    if prog in known_tui:
        return True

    lowered = cmd.lower()
    if "|" in lowered and ("| less" in lowered or "| more" in lowered):
        return True

    # 'su' typically requires a TTY for password prompt; keep interactive
    if prog == "su":
        return True

    # Continuous follow pattern
    if re.search(r"\btail\s+-f\b", lowered):
        return True

    return False


def format_system_context() -> str:
    """
    Format comprehensive system information as context string for the agent.

    This provides all necessary environment details for the agent to make
    informed decisions about which commands to execute.

    Returns:
        Detailed system context string for agent.
    """
    os_name = platform.system()
    os_release = platform.release()
    machine_arch = platform.machine()

    # Get shell information
    if os_name == "Windows":
        # For Windows: try PowerShell, then fallback to CMD
        if shutil.which("pwsh"):
            shell = "pwsh"
        elif shutil.which("powershell"):
            shell = "powershell"
        else:
            shell = "cmd.exe"
    else:
        shell = os.getenv("SHELL", "/bin/sh")
    shell_name = os.path.basename(shell)

    # Get current working directory and user info
    cwd = os.getcwd()
    username = os.getenv("USER", os.getenv("USERNAME", "user"))
    hostname = platform.node().split(".")[0]

    # Detect package managers
    package_managers = []

    if os_name == "Darwin":  # macOS
        package_managers.append("brew")
        if shutil.which("port"):
            package_managers.append("port")
    elif os_name == "Linux":
        # Check for common Linux package managers
        if shutil.which("apt"):
            package_managers.append("apt")
        if shutil.which("yum"):
            package_managers.append("yum")
        if shutil.which("dnf"):
            package_managers.append("dnf")
        if shutil.which("pacman"):
            package_managers.append("pacman")
    elif os_name == "Windows":
        if shutil.which("choco"):
            package_managers.append("choco")
        if shutil.which("winget"):
            package_managers.append("winget")

    # Check for common development tools
    dev_tools = []
    for tool in ["git", "python", "python3", "node", "npm", "docker", "uv", "pip"]:
        if shutil.which(tool):
            dev_tools.append(tool)

    context_parts = [
        f"Operating System: {os_name} {os_release} ({machine_arch})",
        f"Shell: {shell_name} ({shell})",
        f"Current Directory: {cwd}",
        f"User: {username}@{hostname}",
    ]

    if package_managers:
        context_parts.append(f"Package Managers: {', '.join(package_managers)}")

    if dev_tools:
        context_parts.append(f"Available Tools: {', '.join(dev_tools)}")

    # Add OS-specific command notes
    if os_name == "Darwin":
        context_parts.append("Note: macOS uses BSD-style commands (use stat -f, du without GNU options)")
    elif os_name == "Linux":
        context_parts.append("Note: Linux uses GNU-style commands (stat -c, du with GNU options)")
    elif os_name == "Windows":
        context_parts.append(f"Note: Windows shell ({shell_name}) - use PowerShell cmdlets or Windows commands")

    return "\n".join(context_parts)


def get_shell_prompt(agent_mode=False):
    """
    Генерирует приглашение командной строки для shell режима.

    Args:
        agent_mode (bool): True для отображения индикатора агента в приглашении

    Returns:
        str: Строка приглашения командной строки
    """
    from agent.config import get_setting

    user = getpass.getuser()
    hostname = socket.gethostname().split(".")[0]
    current_dir = Path.cwd()

    # Сокращаем путь если он в домашней директории
    home = Path.home()
    if current_dir == home:
        path = "~"
    elif current_dir.is_relative_to(home):
        path = "~/" + str(current_dir.relative_to(home))
    else:
        path = str(current_dir)

    # Добавляем индикатор агента если включен режим агента
    indicator = ""
    if agent_mode:
        agent_indicator = get_setting("agent_prompt_indicator", "⭐")
        if agent_indicator:
            indicator = agent_indicator + " "

    return f"{indicator}{user}@{hostname}:{path}$ "
