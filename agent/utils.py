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
from typing import Dict, Any


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
