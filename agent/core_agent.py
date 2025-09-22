"""
Core LLM Agent - чистая логика обработки запросов с функциями.

Этот модуль содержит только агентскую логику обработки запросов с функциями.
Используется как бэкенд для chat и shell интерфейсов.
"""

from enum import Enum
from typing import Any, Dict, List, Tuple, Union, Optional
import json

from dotenv import load_dotenv

from providers import (
    ADD_FUNCTION_RESULT_TO_MESSAGES,
    EXTRACT_FUNCTION_CALLS,
    EXTRACT_USAGE_INFO,
    GET_AVAILABLE_TOOLS,
    GET_DISPLAY_NAME,
    GET_RESPONSE_TEXT,
    INITIALIZE_CLIENT,
    SEND_MESSAGE,
)
from agent.utils import format_system_context, get_subprocess_kwargs, get_timeout_seconds, should_run_interactive

# Load environment variables from .env file
load_dotenv()


def get_agent_tools() -> List[Dict[str, Any]]:
    """Централизованное определение всех доступных инструментов для агента."""
    return [
        {
            "type": "function",
            "function": {
                "name": "run_shell_command",
                "description": "Execute shell command in terminal and return execution result",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute, e.g. 'ls -la /tmp' or 'grep -r pattern .'",
                        },
                        "estimated_timeout": {
                            "type": "integer",
                            "description": "Estimated timeout in seconds (5-300). Consider command complexity: find/du operations need 60-300s, simple commands like ls/ps need 5-30s",
                            "minimum": 5,
                            "maximum": 300,
                            "default": 30,
                        },
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_agent_configuration",
                "description": "Get current CLI agent configuration settings (read-only)",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_agent_configuration",
                "description": "Update CLI agent configuration settings (default provider, model, mode, prompt indicator, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "default_provider": {"type": "string", "enum": ["openai", "gemini", "lmstudio"], "description": "Default LLM provider (openai, gemini, lmstudio)"},
                        "default_model": {"type": "string", "description": "Default model name (provider-specific, e.g. 'gpt-4', 'gemini-pro', null for provider default)"},
                        "default_mode": {"type": "string", "enum": ["chat", "shell"], "description": "Default startup mode (chat or shell)"},
                        "agent_prompt_indicator": {"type": "string", "description": "Symbol shown in shell prompt when in agent mode (e.g. '⭐', '🤖', '>')"},
                        "preserve_initial_location": {"type": "boolean", "description": "Whether to return to starting directory when exiting shell mode"},
                        "completion_enabled": {"type": "boolean", "description": "Whether to enable tab completion in shell mode"},
                        "history_length": {"type": "integer", "minimum": 1, "description": "Number of commands to keep in history"},
                        "system_prompt_file": {"type": ["string", "null"], "description": "Path to a file with custom system prompt (Markdown/text)"},
                        "system_prompt_text": {"type": ["string", "null"], "description": "Inline custom system prompt text"},
                    },
                    "additionalProperties": False,
                },
            },
        },
    ]


# Configuration constants for the agent
MAX_AGENT_ITERATIONS = 10
MAX_CONTEXT_TOKENS = 4000
HISTORY_TRIM_LINES = 2
MAX_COMMAND_OUTPUT_SIZE = 2000  # Maximum characters for command output

# System prompt used for all providers and modes (chat and shell)
SYSTEM_PROMPT = """You are a terminal agent with cross-platform command-line access (Windows PowerShell/CMD, Linux/Unix shells).

SECURITY RULES:
	•	NEVER install software without explicit user permission.
	•	NEVER execute commands like apt, yum, brew, pip, npm, cargo install unless explicitly allowed.
	•	Check tool availability by trying to run the tool with --version or --help first.
    •	On Windows, use PowerShell commands where possible; on Unix/Linux, use standard shell commands.
	•	If a required tool is missing, clearly state which tool is needed and ask: "To proceed, I need to install [tool]. May I do so?"

EXECUTION STRATEGY:
	1.	Identify necessary commands to fulfill user requests.
	2.	Verify tool availability first.
	3.	Request explicit permission if installation is required.
	4.	Execute commands only after confirming tools are available.
	5.	Carefully analyze command results:
	    •	If successful and enough to fulfill the request, shape the response and continue with no extra functions calls.
		•	If unsuccessful or unclear, adjust and retry (max number of iterations is {MAX_AGENT_ITERATIONS}).
        •	If no solution is found after {MAX_AGENT_ITERATIONS} attempts, explain the issue and suggest alternatives.
	6.	Execute multiple commands sequentially if required, but strategically.

COMMAND ERROR HANDLING:
	•	When user input was attempted as a shell command but failed, help diagnose the issue.
	•	For "command not found" errors, suggest correct spelling, alternatives, or installation.
	•	For permission/syntax errors, provide specific fix suggestions.
	•	Distinguish between typos and legitimate natural language questions.
	•	If user provides context about a failed command, focus on solving that specific issue.

SHELL MODE BEHAVIOR:
	•	In shell mode, respond as concisely as possible while being helpful.
	•	Don't add conversational fluff - be direct and task-focused.
	•	When executing commands successfully, present output cleanly without extra commentary.
	•	When helping with errors, be specific and actionable.

COMPLETION RULES:
	•	ALWAYS present command outputs verbatim immediately after execution - do not process or analyze the output.
	•	Include ALL output lines, regardless of length - never summarize or truncate.
	•	After showing complete output, you may add brief commentary if needed.
	•	If output is very long (>100 lines), show it all but suggest filtering options.
	•	After 2-3 unsuccessful attempts, explain the issue clearly and propose alternatives.
	•	Respond concisely, informatively, and in the user's prompt language.
	•	Maintain original output formatting unless explicitly instructed otherwise.
    •	Result should be visually separated from rest of the response, such as comments, recommendations etc.
"""


class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    GEMINI = "gemini"
    LMSTUDIO = "lmstudio"


# Global configuration for models by provider
PROVIDER_MODELS = {
    LLMProvider.OPENAI: "gpt-5-mini",
    LLMProvider.GEMINI: "gemini-2.5-flash",
    LLMProvider.LMSTUDIO: "gpt-oss-20b",
}


def set_model_for_provider(provider: LLMProvider, model_name: str) -> None:
    """Set the model name for a specific provider."""
    PROVIDER_MODELS[provider] = model_name


def get_model_for_provider(provider: LLMProvider) -> str:
    """Get the model name for a specific provider."""
    return PROVIDER_MODELS[provider]


def _log_command_execution(command: str, silent_mode: bool = False) -> None:
    """Log command execution if not in silent mode, hiding 'which' commands."""
    if not silent_mode and not command.strip().startswith("which "):
        print(f"Executing command: {command}")


def _truncate_output_if_needed(output: str, output_type: str = "STDOUT") -> str:
    """Truncate command output if it's too large, with informative message."""
    if len(output) <= MAX_COMMAND_OUTPUT_SIZE:
        return output

    truncated = output[:MAX_COMMAND_OUTPUT_SIZE]
    remaining_chars = len(output) - MAX_COMMAND_OUTPUT_SIZE
    lines_total = output.count("\n")
    lines_shown = truncated.count("\n")

    truncation_msg = f"\n\n[OUTPUT TRUNCATED: showing first {MAX_COMMAND_OUTPUT_SIZE} characters of {len(output)} total. Remaining: {remaining_chars} chars, approximately {lines_total - lines_shown} more lines. Use filtering commands like 'head', 'tail', 'grep' to see specific parts.]"

    return truncated + truncation_msg


def _prompt_user_to_continue(max_iterations: int) -> bool:
    """Ask the user whether to continue after reaching iteration limit."""
    prompt = f"Reached the iteration limit ({max_iterations}). Do you want to continue? (Y/n) "
    while True:
        try:
            response = input(prompt)
        except EOFError:
            return False

        answer = response.strip().lower()
        if answer in ("", "y", "yes"):
            return True
        if answer in ("n", "no"):
            print("Clarify the task.")
            return False
        print("Please respond with 'Y' to continue or 'N' to clarify the task.")


def execute_tool(function_name: str, function_args: Dict[str, Any], verbose: bool = False) -> str:
    """Execute a shell command tool and return the result."""
    import subprocess

    if function_name == "run_shell_command":
        command = function_args.get("command", "")
        if not command:
            return "Error: Command not specified"

        # Resolve timeout: settings/env can disable timeout entirely
        estimated_timeout = function_args.get("estimated_timeout", None)
        configured_timeout = get_timeout_seconds("tool")
        if configured_timeout is None:
            timeout = None
        else:
            # If LLM estimated a timeout, respect it but cap by configured_timeout
            if isinstance(estimated_timeout, int):
                timeout = min(max(5, estimated_timeout), configured_timeout)
            else:
                timeout = configured_timeout

        if verbose:
            print(f"[DEBUG] Using timeout: {timeout if timeout is not None else 'none'} (estimated: {estimated_timeout})")

        try:
            # Execute command through shell
            subprocess_kwargs = get_subprocess_kwargs()

            # Interactive detection similar to shell mode
            if should_run_interactive(command):
                if verbose:
                    print("[DEBUG] Detected interactive/TUI command; attaching to TTY")
                subprocess_kwargs.pop("text", None)
                subprocess_kwargs["capture_output"] = False
                subprocess_kwargs.pop("timeout", None)
                result = subprocess.run(command, **subprocess_kwargs)
                # No captured output; return minimal info
                return f"Exit code: {result.returncode}\nSTDOUT:\n\nSTDERR:\n"
            else:
                # Captured mode. For sudo: two-phase flow — interactive 'sudo -v', then 'sudo -n ...' captured
                if timeout is not None:
                    subprocess_kwargs.update({"timeout": timeout})

                cmd_str = command.strip()
                if cmd_str.startswith("sudo "):
                    # Phase 1: refresh sudo timestamp interactively
                    interactive_kwargs = get_subprocess_kwargs()
                    interactive_kwargs.pop("text", None)
                    interactive_kwargs["capture_output"] = False
                    interactive_kwargs.pop("timeout", None)
                    subprocess.run("sudo -v", **interactive_kwargs)

                    # Phase 2: run original with 'sudo -n ...' captured
                    parts = cmd_str.split(maxsplit=1)
                    suffix = parts[1] if len(parts) > 1 else ""
                    cmd_run = f"sudo -n {suffix}".strip()
                    result = subprocess.run(cmd_run, **subprocess_kwargs)
                else:
                    result = subprocess.run(cmd_str, **subprocess_kwargs)

            if verbose:
                stdout_lines = result.stdout.count("\n") if result.stdout else 0
                print(f"[DEBUG] Command output: {len(result.stdout) if result.stdout else 0} chars, {stdout_lines} lines")

            # Truncate large outputs to prevent context overflow
            stdout_output = _truncate_output_if_needed(result.stdout) if result.stdout else ""
            stderr_output = _truncate_output_if_needed(result.stderr, "STDERR") if result.stderr else ""

            return f"Exit code: {result.returncode}\nSTDOUT:\n{stdout_output}\nSTDERR:\n{stderr_output}"

        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"

    elif function_name == "get_agent_configuration":
        from agent.config import load_settings

        settings = load_settings()
        return json.dumps({"success": True, "settings": settings}, ensure_ascii=False)

    elif function_name == "update_agent_configuration":
        from agent.config import update_configuration

        if verbose:
            print(f"[DEBUG] Updating configuration with: {function_args}")

        result = update_configuration(function_args)

        if verbose:
            print(f"[DEBUG] Configuration update result: {result}")

        # Return human-readable result
        if result["success"]:
            return f"Configuration updated successfully!\n{result['message']}\nUpdated settings: {result['updated_settings']}"
        else:
            return f"Configuration update failed: {result['message']}"

    else:
        return f"Unknown function: {function_name}"


def should_show_trace() -> bool:
    """Check if trace output should be shown based on environment."""
    import os

    return os.getenv("CLI_AGENT_TRACE", "").lower() in ("1", "true", "yes") or os.getenv("TRACE", "false").lower() == "true"


def trim_history_if_needed(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Trim message history if it's getting too long."""
    if len(messages) > MAX_CONTEXT_TOKENS:
        # Keep system message and last HISTORY_TRIM_LINES messages
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        recent_messages = messages[-HISTORY_TRIM_LINES:]
        return system_messages + recent_messages
    return messages


def _load_custom_system_prompt_from_env() -> Optional[str]:
    """Load custom system prompt from environment variables if provided.

    Supports:
    - CLI_AGENT_SYSTEM_PROMPT_FILE: path to a file with prompt content
    - CLI_AGENT_SYSTEM_PROMPT: inline prompt text
    """
    import os

    file_path = os.getenv("CLI_AGENT_SYSTEM_PROMPT_FILE")
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
    text = os.getenv("CLI_AGENT_SYSTEM_PROMPT")
    if text and text.strip():
        return text
    return None


def _load_custom_system_prompt_from_settings() -> Optional[str]:
    """Load custom system prompt from persistent settings if present."""
    try:
        from agent.config import get_setting

        file_path = get_setting("system_prompt_file", None)
        if isinstance(file_path, str) and file_path.strip():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass

        text = get_setting("system_prompt_text", None)
        if isinstance(text, str) and text.strip():
            return text
    except Exception:
        pass
    return None


def _format_custom_prompt(raw_prompt: str) -> str:
    """Format custom prompt, preserving placeholders where applicable."""
    try:
        return raw_prompt.format(MAX_AGENT_ITERATIONS=MAX_AGENT_ITERATIONS)
    except Exception:
        return raw_prompt


def get_system_prompt(shell_mode: bool = False) -> str:
    """Get system prompt with support for custom extensions via ENV/settings."""
    base_prompt = SYSTEM_PROMPT.format(MAX_AGENT_ITERATIONS=MAX_AGENT_ITERATIONS)

    custom = _load_custom_system_prompt_from_env() or _load_custom_system_prompt_from_settings()
    if custom:
        custom_formatted = _format_custom_prompt(custom)
        return f"{base_prompt}\n\nCUSTOM INSTRUCTIONS:\n{custom_formatted.strip()}"

    return base_prompt


def process_user_message(
    user_input: str,
    provider: LLMProvider,
    client: Any,
    chat_history: Dict[str, Any],
    return_usage: bool = False,
    verbose: bool = False,
    silent_mode: bool = False,
    shell_mode: bool = False,
) -> Union[str, Tuple[str, Dict[str, Any]]]:
    """
    Core agent function: processes user request with function calling capabilities.

    Responsibilities:
    - Initializes chat history with system prompt on first call
    - Manages conversation context across multiple requests
    - Handles function calling and multi-iteration execution
    - Returns either text response or response with usage statistics

    Args:
        user_input: The user's request/message
        provider: LLM provider (OpenAI, Gemini, LMStudio)
        client: Initialized client for the provider
        chat_history: Persistent conversation history (managed by this function)
        return_usage: Whether to return token usage statistics
        verbose: Show detailed execution information
        silent_mode: Suppress intermediate output
        shell_mode: Running in shell mode (affects system prompt)

    Returns:
        str: Response text (if return_usage=False)
        Tuple[str, Dict]: Response text and usage stats (if return_usage=True)
    """
    trace_enabled = should_show_trace()

    if trace_enabled and not silent_mode:
        print(f"[TRACE] Processing message: {user_input}")
        print(f"[TRACE] Provider: {provider.value}")

    # Initialize chat history if needed
    if "messages" not in chat_history:
        system_context = format_system_context()
        system_message = get_system_prompt(shell_mode)
        # Use proper message format for compatibility
        chat_history["messages"] = [{"role": "system", "content": f"{system_message}\n\n{system_context}"}]

    # Add user message
    chat_history["messages"].append({"role": "user", "content": user_input})

    # Trim history if needed
    chat_history["messages"] = trim_history_if_needed(chat_history["messages"])

    iteration_count = 0
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    max_iterations = MAX_AGENT_ITERATIONS

    while True:
        while iteration_count < max_iterations:
            iteration_count += 1

            if trace_enabled and not silent_mode:
                print(f"[TRACE] Iteration {iteration_count}/{max_iterations}")

            try:
                # Get current model and available tools for debug
                current_model = get_model_for_provider(provider)
                available_tools = GET_AVAILABLE_TOOLS[provider.value]()

                # Debug output when trace is enabled
                if trace_enabled and not silent_mode:
                    print("\n[DEBUG] === REQUEST TO MODEL ===")
                    print(f"[DEBUG] Provider: {provider.value}")
                    print(f"[DEBUG] Model: {current_model}")
                    print(f"[DEBUG] Shell mode: {shell_mode}")
                    print(f"[DEBUG] Messages count: {len(chat_history['messages'])}")

                    # Show system message
                    for i, msg in enumerate(chat_history["messages"]):
                        if msg.get("role") == "system":
                            print(f"[DEBUG] System message {i + 1}:")
                            print(f"[DEBUG] Content: {msg['content'][:500]}{'...' if len(msg['content']) > 500 else ''}")
                        elif msg.get("role") == "user":
                            print(f"[DEBUG] User message {i + 1}: {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}")
                        elif msg.get("role") == "assistant":
                            print(f"[DEBUG] Assistant message {i + 1}: {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}")

                    # Show available tools
                    print(f"[DEBUG] Available tools: {len(available_tools)}")
                    for tool in available_tools:
                        if isinstance(tool, dict) and "function" in tool:
                            print(f"[DEBUG] Tool: {tool['function']['name']} - {tool['function']['description'][:100]}...")
                    print("[DEBUG] === END REQUEST DEBUG ===\n")

                # Send message to LLM
                response_data = SEND_MESSAGE[provider.value](
                    client,
                    chat_history["messages"],
                    current_model,  # type: ignore
                )

                # Extract usage info if available
                usage_info = EXTRACT_USAGE_INFO[provider.value](response_data)
                if usage_info:
                    for key in total_usage:
                        total_usage[key] += usage_info.get(key, 0)

                # Extract response text
                response_text = GET_RESPONSE_TEXT[provider.value](response_data)

                # Extract function calls
                function_calls = EXTRACT_FUNCTION_CALLS[provider.value](response_data)

                if not function_calls:
                    # No function calls - final response
                    chat_history["messages"].append({"role": "assistant", "content": response_text})

                    if trace_enabled and not silent_mode:
                        print(f"[TRACE] Final response (iteration {iteration_count})")

                    if return_usage:
                        return response_text, total_usage
                    return response_text

                # Execute function calls
                if not silent_mode:
                    print(f"Executing {len(function_calls)} function(s)...")

                chat_history["messages"].append({"role": "assistant", "content": response_text})

                function_results = []
                for function_call in function_calls:
                    function_name = function_call["name"]
                    function_args = function_call["arguments"]

                    command = function_args.get("command", "N/A")
                    _log_command_execution(command, silent_mode)

                    result = execute_tool(function_name, function_args, verbose)
                    function_results.append(result)

                ADD_FUNCTION_RESULT_TO_MESSAGES[provider.value](
                    chat_history["messages"],
                    response_data,
                    function_results,  # type: ignore
                )

                if trace_enabled and not silent_mode:
                    print(f"[TRACE] Executed {len(function_calls)} function(s), continuing...")

            except Exception as e:
                error_msg = f"Error in iteration {iteration_count}: {str(e)}"
                if not silent_mode:
                    print(f"❌ {error_msg}")

                if return_usage:
                    return error_msg, total_usage
                return error_msg

        if not silent_mode and _prompt_user_to_continue(max_iterations):
            max_iterations += MAX_AGENT_ITERATIONS
            continue
        break

    final_response = f"Reached the iteration limit ({max_iterations}). Do you want to continue? (Y/n)"
    if not silent_mode:
        print(f"⚠️  {final_response}")

    if "messages" in chat_history:
        chat_history["messages"].append({"role": "assistant", "content": final_response})

    if return_usage:
        return final_response, total_usage
    return final_response


class AgentConfig:
    """
    Configuration container for LLM agent.

    Manages provider settings, model selection, client initialization,
    and persistent conversation history. Used by both chat and shell interfaces.

    Attributes:
        provider: LLM provider (OpenAI, Gemini, LMStudio)
        model: Model name for the provider
        client: Initialized client instance for API calls
        chat_history: Persistent conversation history (dict with 'messages' list)
    """

    def __init__(self, provider: LLMProvider, model: Optional[str] = None):
        """
        Initialize agent configuration.

        Args:
            provider: LLM provider to use
            model: Specific model name (optional, uses default if not provided)
        """
        self.provider = provider
        self.model = model or get_model_for_provider(provider)
        self.client = None
        self.chat_history = {}  # Will be initialized by process_user_message

    def initialize_client(self):
        """Initialize the LLM client for API communication."""
        if self.model != get_model_for_provider(self.provider):
            set_model_for_provider(self.provider, self.model)

        self.client = INITIALIZE_CLIENT[self.provider.value]()
        return self.client

    def get_provider_display_name(self) -> str:
        """Get human-readable display name for the provider and model."""
        return GET_DISPLAY_NAME[self.provider.value](self.model)
