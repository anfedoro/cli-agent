"""Shell-like interface that intelligently routes commands to shell or LLM.

This module provides a shell-like interface where:
- Direct shell commands (ls, cd, grep) are executed immediately
- Natural language requests are processed by LLM
- Standard shell prompt and tab completion are supported
- LLM execution traces are shown only when CLI_AGENT_TRACE env var is set
"""

import os
import subprocess
import sys
from typing import Optional, Tuple

from core_agent import AgentConfig, LLMProvider, process_user_message
from input_handler import enhanced_input, is_readline_available
from utils import get_shell_prompt


# Common shell commands that should be executed directly
SHELL_COMMANDS = {
    "ls",
    "cd",
    "pwd",
    "mkdir",
    "rmdir",
    "rm",
    "cp",
    "mv",
    "chmod",
    "chown",
    "cat",
    "less",
    "more",
    "head",
    "tail",
    "grep",
    "find",
    "which",
    "whereis",
    "ps",
    "top",
    "kill",
    "jobs",
    "bg",
    "fg",
    "nohup",
    "df",
    "du",
    "free",
    "mount",
    "umount",
    "tar",
    "gzip",
    "gunzip",
    "zip",
    "unzip",
    "curl",
    "wget",
    "ssh",
    "scp",
    "rsync",
    "git",
    "svn",
    "pip",
    "npm",
    "yarn",
    "uv",
    "echo",
    "printf",
    "date",
    "cal",
    "uptime",
    "whoami",
    "id",
    "history",
    "alias",
    "export",
    "env",
    "set",
    "unset",
    "make",
    "cmake",
    "gcc",
    "g++",
    "python",
    "python3",
    "node",
    "java",
    "vim",
    "nano",
    "emacs",
    "code",
    "clear",
    "reset",
    "exit",
    "logout",
}


def smart_execute_with_fallback(input_text: str, config: AgentConfig) -> Tuple[bool, str]:
    """Smart execution: try shell first, fallback to LLM if needed.

    Returns:
        Tuple of (is_shell_result, output)
    """
    trace_enabled = should_show_trace()

    # First, try to execute as shell command
    if trace_enabled:
        print(f"[TRACE] Trying shell execution: {input_text}")

    exit_code, stdout, stderr = execute_shell_command(input_text)

    # If command succeeded, return shell result
    if exit_code == 0:
        if trace_enabled:
            print("[TRACE] Shell execution successful")
        output = stdout if stdout else "(no output)"
        return True, output

    # If command failed, analyze the failure
    if trace_enabled:
        print(f"[TRACE] Shell execution failed (exit code: {exit_code})")
        print(f"[TRACE] Error: {stderr}")

    # Check if this looks like a genuine command failure vs natural language
    if looks_like_command_failure(input_text, stderr):
        # For "command not found" errors, send to LLM for intelligent help
        if "command not found" in stderr.lower():
            if trace_enabled:
                print("[TRACE] Command not found - sending to LLM for help")
            llm_response = process_llm_request(input_text, config)
            return False, llm_response
        else:
            # Other command errors (permission denied, etc.) - show as shell error
            if trace_enabled:
                print("[TRACE] Command error - showing shell error")
            error_output = stderr if stderr else f"Command failed with exit code {exit_code}"
            return True, error_output

    # This is probably natural language - send to LLM
    if trace_enabled:
        print("[TRACE] Treating as natural language, sending to LLM")

    llm_response = process_llm_request(input_text, config)
    return False, llm_response


def looks_like_command_failure(input_text: str, error_message: str) -> bool:
    """Determine if a failed execution was intended as a command."""

    # Check error message patterns that indicate genuine command attempts
    command_error_patterns = [
        "command not found",
        "No such file or directory",
        "Permission denied",
        "not a directory",
        "is a directory",
        "Invalid option",
        "Usage:",
        "illegal option",
        "unknown option",
    ]

    error_lower = error_message.lower()
    for pattern in command_error_patterns:
        if pattern.lower() in error_lower:
            # Additional check: simple/short input is more likely a command
            words = input_text.strip().split()
            if len(words) <= 3:  # Short inputs are likely commands
                return True
            break

    return False


def is_shell_command(input_text: str) -> bool:
    """Legacy function - now we use smart_execute_with_fallback instead.

    Kept for backward compatibility with tests.
    """
    # Simplified logic since we now rely on smart execution
    if not input_text.strip():
        return False

    # Only obvious cases that we know should be shell commands
    shell_operators = ["|", ">", ">>", "<", "&&", "||", ";", "&"]
    if any(op in input_text for op in shell_operators):
        return True

    # Paths
    if input_text.startswith("./") or input_text.startswith("/") or input_text.startswith("~/"):
        return True

    # For everything else, let smart_execute_with_fallback decide
    return False


def execute_shell_command(command: str) -> Tuple[int, str, str]:
    """Execute shell command and return (exit_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timeout (5 minutes exceeded)"
    except Exception as e:
        return 1, "", f"Execution error: {str(e)}"


def should_show_trace() -> bool:
    """Check if trace mode is enabled via environment variable."""
    return os.getenv("CLI_AGENT_TRACE", "").lower() in ("1", "true", "yes")


def process_llm_request(request: str, config: AgentConfig) -> str:
    """Send request to core agent and return response."""
    trace_enabled = should_show_trace()

    if trace_enabled:
        print(f"[TRACE] Processing LLM request: {request}")
        print(f"[TRACE] Provider: {config.provider.value}, Model: {config.model}")

    try:
        if trace_enabled:
            response, usage_info = process_user_message(
                request, config.provider, config.client, config.chat_history, return_usage=True, verbose=True, silent_mode=False, shell_mode=True
            )
            print(f"[TRACE] Token usage: {usage_info}")
            return response
        else:
            result = process_user_message(request, config.provider, config.client, config.chat_history, return_usage=False, verbose=False, silent_mode=False, shell_mode=True)
            return result if isinstance(result, str) else result[0]
    except Exception as e:
        return f"Error processing LLM request: {str(e)}"


def shell_main(provider: str = "openai", model: Optional[str] = None, trace: bool = False) -> None:
    """Main shell interface function.

    Args:
        provider: LLM provider to use ("openai", "gemini", or "lmstudio")
        model: Model name to use for the selected provider (optional)
        trace: Enable trace mode (overrides CLI_AGENT_TRACE env var)
    """
    # Set trace environment if requested
    if trace:
        os.environ["CLI_AGENT_TRACE"] = "1"

    # Initialize LLM provider
    try:
        if provider == "openai":
            llm_provider = LLMProvider.OPENAI
        elif provider == "gemini":
            llm_provider = LLMProvider.GEMINI
        elif provider == "lmstudio":
            llm_provider = LLMProvider.LMSTUDIO
        else:
            print(f"Error: Unsupported provider '{provider}'. Use 'openai', 'gemini', or 'lmstudio'.")
            return

        # Create agent configuration with persistent history
        config = AgentConfig(llm_provider, model)
        config.initialize_client()

        # Let core_agent initialize chat history properly
        # config.chat_history will be initialized by process_user_message when needed

        if should_show_trace():
            print(f"[TRACE] Initialized {config.get_provider_display_name()}")
            if is_readline_available():
                print("[TRACE] Readline: enabled, command history and tab completion available")
            else:
                print("[TRACE] Readline: not available (basic input mode)")

    except ValueError as e:
        print(f"Error: {e}")
        return

    # Main shell loop
    while True:
        try:
            # Get shell prompt (standard format)
            prompt = get_shell_prompt()
            user_input = enhanced_input(prompt).strip()

            if not user_input:
                continue

            # Handle exit commands
            if user_input.lower() in ["exit", "quit", "logout"]:
                break

            # Handle special shell commands
            if user_input == "clear":
                os.system("clear")
                continue

            # Use smart execution with LLM fallback
            is_shell_result, output = smart_execute_with_fallback(user_input, config)

            if output:
                if is_shell_result:
                    # Shell command result - print directly
                    print(output, end="" if output.endswith("\n") else "\n")
                else:
                    # LLM response - print normally
                    print(output)

        except KeyboardInterrupt:
            print()  # New line after ^C
            continue
        except EOFError:
            print()  # New line after ^D
            break
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    shell_main()
