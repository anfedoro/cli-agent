import subprocess
from enum import Enum
from typing import Any, Dict, List, Tuple, Union

from dotenv import load_dotenv

from input_handler import cleanup_input_handler, enhanced_input, is_readline_available
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
from providers.lmstudio import is_no_reasoning, set_no_reasoning
from utils import format_system_context

# Load environment variables from .env file
load_dotenv()

# Configuration constants for the agent
# Maximum number of iterations for the agent to refine its response
MAX_AGENT_ITERATIONS = 10

# Configuration constants for history management
MAX_CONTEXT_TOKENS = 4000
HISTORY_TRIM_LINES = 2

# System prompt used for all providers
SYSTEM_PROMPT = """You are a terminal agent with access to Linux/Unix command-line tools (ls, grep, find, cat, ps, df, etc.).

SECURITY RULES:
	•	NEVER install software without explicit user permission.
	•	NEVER execute commands like apt, yum, brew, pip, npm, cargo install unless explicitly allowed.
	•	Check tool availability using [which [tool]] or [[tool] --version.]
	•	If a required tool is missing, clearly state which tool is needed and ask: “To proceed, I need to install [tool]. May I do so?”

EXECUTION STRATEGY:
	1.	Identify necessary commands to fulfill user requests.
	2.	Verify tool availability first.
	3.	Request explicit permission if installation is required.
	4.	Execute commands only after confirming tools are available.
	5.	Carefully analyze command results:
	    •	If successful and informative, continue.
		•	If unsuccessful or unclear, adjust and retry (max 2-3 attempts).
	6.	Execute multiple commands sequentially if required, but strategically.

COMPLETION RULES:
	•	Prefferably present COMPLETE command outputs verbatim—never summarize or truncate until explicitely asked to reformat output.
	•	Include ALL output lines, regardless of length.
	•	Clearly show actual results; do not generalize or simplify.
	•	After 2-3 unsuccessful attempts, explain the issue clearly and propose alternatives.
	•	Respond concisely, informatively, and in the user’s prompt language.
	•	Maintain original output formatting unless explicitly instructed otherwise.
"""


class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    GEMINI = "gemini"
    LMSTUDIO = "lmstudio"


# Global configuration for models by provider
PROVIDER_MODELS = {
    LLMProvider.OPENAI: "gpt-4.1-mini",
    LLMProvider.GEMINI: "gemini-2.5-flash",
    LLMProvider.LMSTUDIO: "Qwen3-8B-MLX-4bit",  # note that the only models with tools support are possible to use
}


def set_model_for_provider(provider: LLMProvider, model_name: str) -> None:
    """Set the model name for a specific provider."""
    PROVIDER_MODELS[provider] = model_name


def get_model_for_provider(provider: LLMProvider) -> str:
    """Get the model name for a specific provider."""
    return PROVIDER_MODELS[provider]


def execute_tool(tool_name: str, arguments: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    """Execute specified tool with given arguments."""
    if tool_name == "run_shell_command":
        command = arguments.get("command", "")
        if not command:
            return {"success": False, "error": "Command not specified"}

        # Get timeout from LLM estimation or use default
        estimated_timeout = arguments.get("estimated_timeout", 30)
        # Ensure timeout is within reasonable bounds
        timeout = max(5, min(300, estimated_timeout))

        if verbose:
            print(f"[DEBUG] Using timeout: {timeout}s (estimated: {estimated_timeout}s)")

        try:
            # Execute command through shell
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            # Debug: show output length (only in verbose mode)
            if verbose:
                stdout_lines = result.stdout.count("\n") if result.stdout else 0
                print(f"[DEBUG] Command output: {len(result.stdout) if result.stdout else 0} chars, {stdout_lines} lines")

            return {"success": True, "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode, "command": command}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command execution timeout exceeded ({timeout} sec)"}
        except Exception as e:
            return {"success": False, "error": f"Command execution error: {str(e)}"}

    return {"success": False, "error": f"Unknown tool: {tool_name}"}


def add_to_history(history: Dict[str, Any], line: str) -> None:
    """Add line to chat history."""
    history["lines"].append(line)


def trim_history_lines(history: Dict[str, Any]) -> None:
    """Remove old lines from history if it gets too long."""
    if len(history["lines"]) > HISTORY_TRIM_LINES * 2:  # Keep some buffer
        # Remove oldest lines
        lines_to_remove = HISTORY_TRIM_LINES
        history["lines"] = history["lines"][lines_to_remove:]


def format_history_for_prompt(history: Dict[str, Any]) -> str:
    """Convert history lines to text for API prompt."""
    return "\n".join(history["lines"])


def _log_command_execution(command: str) -> None:
    """Log command execution for debugging purposes."""
    print(f"Executing command: {command}")


def initialize_client(provider: LLMProvider) -> Any:
    """Initialize client for the specified provider."""
    return INITIALIZE_CLIENT[provider.value]()


def get_available_tools(provider: LLMProvider) -> List[Any]:
    """Get available tools for the specified provider."""
    return GET_AVAILABLE_TOOLS[provider.value]()


def get_display_name(provider: LLMProvider, model_name: str) -> str:
    """Get display name for the specified provider with model name."""
    return GET_DISPLAY_NAME[provider.value](model_name)


def process_user_message(
    user_prompt: str,
    provider: LLMProvider,
    client_or_model: Any,
    history: Dict[str, Any] | None = None,
    return_usage: bool = False,
    verbose: bool = False,
) -> Union[str, Tuple[str, Dict[str, Any]]]:
    """Process user message through the specified provider using unified agent loop."""

    # Add system context to help agent adapt to current environment
    system_context = format_system_context()

    # Include history context if available
    full_prompt = user_prompt
    if history and history["lines"]:
        history_text = format_history_for_prompt(history)
        full_prompt = f"{history_text}\n{user_prompt}"

    # Prepend system context to the user prompt
    full_prompt = f"{system_context}\n\nUser request: {full_prompt}"

    # Debug: print system context being added
    if verbose:
        print(f"[DEBUG] Adding system context: {system_context}")

    try:
        max_iterations = MAX_AGENT_ITERATIONS
        iteration = 0
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # Provider-specific initialization
        from openai.types.chat import ChatCompletionMessageParam

        messages: List[ChatCompletionMessageParam] = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": full_prompt}]

        if provider not in [LLMProvider.OPENAI, LLMProvider.GEMINI, LLMProvider.LMSTUDIO]:
            raise ValueError(f"Unsupported provider: {provider}")

        # Main agent loop
        while iteration < max_iterations:
            iteration += 1
            if verbose:
                print(f"[DEBUG] Iteration {iteration}/{max_iterations}")

            # Send message to provider
            current_model = get_model_for_provider(provider)
            response = SEND_MESSAGE[provider.value](client_or_model, messages, current_model)

            # Extract usage information
            usage_info = EXTRACT_USAGE_INFO[provider.value](response)

            # Update total usage
            total_usage["prompt_tokens"] += usage_info["prompt_tokens"]
            total_usage["completion_tokens"] += usage_info["completion_tokens"]
            total_usage["total_tokens"] += usage_info["total_tokens"]

            if history is not None:
                history["total_tokens"] += usage_info["total_tokens"]
                if history["total_tokens"] > MAX_CONTEXT_TOKENS:
                    trim_history_lines(history)

            # Extract function calls
            function_calls = EXTRACT_FUNCTION_CALLS[provider.value](response)

            # Execute function calls if any
            if function_calls:
                function_results = []
                for function_call in function_calls:
                    function_name = function_call["name"]
                    function_args = function_call["arguments"]

                    command = function_args.get("command", "N/A")
                    _log_command_execution(command)

                    result = execute_tool(function_name, function_args, verbose)
                    function_results.append(result)

                # Add results back to conversation
                ADD_FUNCTION_RESULT_TO_MESSAGES[provider.value](messages, response, function_results)

                if verbose:
                    print("[DEBUG] Tool execution completed, continuing loop")
                continue
            else:
                # No function calls - return final answer
                if verbose:
                    print("[DEBUG] No more tools to execute, returning final answer")

                content = GET_RESPONSE_TEXT[provider.value](response)

                if not content:
                    content = "No response received from the model."

                if return_usage:
                    return content, total_usage
                return content

        error_msg = "Maximum iterations reached. Please try to simplify your request."
        return (error_msg, total_usage) if return_usage else error_msg

    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        return (error_msg, {}) if return_usage else error_msg


def main(verbose: bool = False, provider: str = "openai", model: str | None = None, no_reasoning: bool = False) -> None:
    """Main function for interactive agent communication.

    Args:
        verbose: Show detailed token usage information
        provider: LLM provider to use ("openai", "gemini", or "lmstudio")
        model: Model name to use for the selected provider (optional)
        no_reasoning: Disable reasoning process for faster responses (LM Studio)
    """
    print(f"LLM Terminal Agent started with {provider.upper()} provider!")
    print("You can ask to execute any Linux commands: ls, grep, find, ps, etc.")
    print("To exit type: quit, exit, or q")
    print("-" * 50)

    # Initialize the selected provider
    try:
        if provider == "openai":
            llm_provider = LLMProvider.OPENAI
            if model:
                set_model_for_provider(llm_provider, model)
        elif provider == "gemini":
            llm_provider = LLMProvider.GEMINI
            if model:
                set_model_for_provider(llm_provider, model)
        elif provider == "lmstudio":
            llm_provider = LLMProvider.LMSTUDIO
            if model:
                set_model_for_provider(llm_provider, model)
        else:
            print(f"Error: Unsupported provider '{provider}'. Use 'openai', 'gemini', or 'lmstudio'.")
            return

        client_or_model = initialize_client(llm_provider)
        current_model = get_model_for_provider(llm_provider)
        print(f"Using {get_display_name(llm_provider, current_model)}")

        if no_reasoning and llm_provider == LLMProvider.LMSTUDIO:
            set_no_reasoning(True)
            print("[INFO] Reasoning disabled for faster responses")

    except ValueError as e:
        print(f"Error: {e}")
        return

    # Initialize chat history
    chat_history = {"lines": [], "total_tokens": 0}

    # Show input handler status in verbose mode
    if verbose:
        if is_readline_available():
            print("[DEBUG] Readline: enabled, command history available")
        else:
            print("[DEBUG] Readline: not available (basic input mode)")

    while True:
        try:
            user_input = enhanced_input("\nUser: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            if user_input.lower() in ["/clear"]:
                print("Clearing chat history...")
                chat_history = {"lines": [], "total_tokens": 0}
                continue

            if not user_input:
                continue

            print("Agent is analyzing request...")
            add_to_history(chat_history, f"User: {user_input}")

            if is_no_reasoning():
                user_input = f"/nothink\n{user_input}"

            if verbose:
                response, usage_info = process_user_message(user_input, llm_provider, client_or_model, chat_history, return_usage=True, verbose=True)
            else:
                response = process_user_message(user_input, llm_provider, client_or_model, chat_history, return_usage=False, verbose=False)

            # some models add \n\n at the beginning of the response, thus we remove it
            if response.startswith("\n\n"):
                response = response[2:]

            add_to_history(chat_history, f"Agent: {response}")
            print(f"\nAgent: {response}")

            # Show detailed token usage in verbose mode
            if verbose:
                try:
                    response, usage_info = locals()["response"], locals()["usage_info"]
                    if usage_info:
                        print(
                            f"\n[Token Usage] Prompt: {usage_info.get('prompt_tokens', 0)}, "
                            f"Completion: {usage_info.get('completion_tokens', 0)}, "
                            f"Total: {usage_info.get('total_tokens', 0)}"
                        )
                        print(f"[Session Total] {chat_history['total_tokens']} tokens, History: {len(chat_history['lines'])} lines")
                except (NameError, KeyError):
                    pass

        except KeyboardInterrupt:
            print("\n\nInterrupt signal received. Goodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")

    # Cleanup input handler before exit
    cleanup_input_handler()


if __name__ == "__main__":
    main()
