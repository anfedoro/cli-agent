"""Shell-like interface that intelligently routes commands to shell or LLM.

This module provides a shell-like interface where:
- Commands are executed directly in shell first
- If command fails with "command not found", route to LLM for help
- Natural language requests are processed by LLM
- Standard shell prompt and tab completion are supported
- LLM execution traces are shown only when CLI_AGENT_TRACE env var is set
"""

import os
import platform
import subprocess
import sys
from typing import Optional, Tuple

from agent.core_agent import AgentConfig, LLMProvider, process_user_message
from input_handler.input_handler import enhanced_input, is_readline_available, cleanup_input_handler
from agent.utils import get_shell_prompt, get_subprocess_kwargs


def clear_screen():
    """Clear screen in a cross-platform way."""
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")


def smart_execute_with_fallback(input_text: str, config: AgentConfig) -> Tuple[bool, str]:
    """Smart execution: try shell first, fallback to LLM if needed.

    Universal approach: always try shell first, then decide based on result.

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
        # Return stdout as-is, empty output is fine (like cd, mkdir, etc.)
        return True, stdout

    # If command failed, analyze the failure
    if trace_enabled:
        print(f"[TRACE] Shell execution failed (exit code: {exit_code})")
        print(f"[TRACE] Error: {stderr}")

    # Check if this looks like a "command not found" error (cross-platform)
    command_not_found_indicators = [
        "command not found",           # Unix/Linux
        "not found",                   # Generic
        "is not recognized",           # Windows PowerShell/CMD
        "not recognized as",           # Windows PowerShell
    ]
    
    is_command_not_found = any(indicator in stderr.lower() for indicator in command_not_found_indicators)
    
    if is_command_not_found:
        # This might be natural language or a typo - send to LLM for help
        if trace_enabled:
            print("[TRACE] Command not found - sending to LLM for help")
        llm_response = process_llm_request(input_text, config)
        return False, llm_response
    else:
        # Other command errors (permission denied, file not found, etc.) - show as shell error
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
        "not found",
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


def execute_shell_command(command: str) -> Tuple[int, str, str]:
    """Execute shell command and return (exit_code, stdout, stderr)."""
    try:
        # Handle built-in shell commands that need special treatment
        command_parts = command.strip().split()
        if not command_parts:
            return 0, "", ""

        cmd = command_parts[0]

        # Handle 'cd' command specially since it needs to change the current process directory
        if cmd == "cd":
            try:
                if len(command_parts) == 1:
                    # cd without arguments goes to home directory
                    target_dir = os.path.expanduser("~")
                else:
                    # cd with path argument
                    target_dir = os.path.expanduser(command_parts[1])

                # Change the current working directory of the Python process
                os.chdir(target_dir)
                return 0, "", ""  # cd doesn't produce output on success

            except FileNotFoundError:
                return 1, "", f"cd: {target_dir}: No such file or directory"
            except PermissionError:
                return 1, "", f"cd: {target_dir}: Permission denied"
            except Exception as e:
                return 1, "", f"cd: {str(e)}"

        # Handle 'pwd' command to show current directory
        elif cmd == "pwd":
            return 0, os.getcwd() + "\n", ""

        # For all other commands, use subprocess as before
        subprocess_kwargs = get_subprocess_kwargs()
        subprocess_kwargs.update(
            {
                "timeout": 300,  # 5 minute timeout
            }
        )

        result = subprocess.run(command, **subprocess_kwargs)
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


def shell_main(provider: str = "openai", model: Optional[str] = None, trace: bool = False, preserve_initial_location: Optional[bool] = None) -> None:
    """Main shell interface function.

    Args:
        provider: LLM provider to use ("openai", "gemini", or "lmstudio")
        model: Model name to use for the selected provider (optional)
        trace: Enable trace mode (overrides CLI_AGENT_TRACE env var)
        preserve_initial_location: Override config setting for preserving initial directory
    """
    # Store initial working directory for potential restoration
    initial_cwd = os.getcwd()

    # Load settings to check preserve_initial_location
    from agent.config import get_setting

    if preserve_initial_location is not None:
        # Use CLI argument override
        preserve_location = preserve_initial_location
    else:
        # Use config file setting
        preserve_location = get_setting("preserve_initial_location", True)

    # Set trace environment if requested
    if trace:
        os.environ["CLI_AGENT_TRACE"] = "1"

    try:
        # Initialize LLM provider
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
            print(f"[TRACE] Preserve initial location: {preserve_location}")

    except ValueError as e:
        print(f"Error: {e}")
        return

    try:
        # Main shell loop
        while True:
            try:
                # Get shell prompt with agent indicator
                prompt = get_shell_prompt(agent_mode=True)
                user_input = enhanced_input(prompt).strip()

                if not user_input:
                    continue

                # Handle exit commands
                if user_input.lower() in ["exit", "quit", "logout"]:
                    break

                # Handle special shell commands
                if user_input == "clear":
                    clear_screen()
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

    finally:
        # Cleanup input handler to save history
        cleanup_input_handler()
        
        # Restore initial directory if preserve_initial_location is True
        if preserve_location:
            try:
                os.chdir(initial_cwd)
                if should_show_trace():
                    print(f"[TRACE] Restored initial directory: {initial_cwd}")
            except Exception as e:
                if should_show_trace():
                    print(f"[TRACE] Failed to restore initial directory: {e}")


if __name__ == "__main__":
    shell_main()
