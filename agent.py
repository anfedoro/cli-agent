import subprocess
from enum import Enum
from typing import Any, Dict, List, Tuple, Union

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

# Load environment variables from .env file
load_dotenv()

# Configuration constants for history management
MAX_CONTEXT_TOKENS = 4000
HISTORY_TRIM_LINES = 5

# System prompt used for all providers
SYSTEM_PROMPT = """You are a terminal agent with access to Linux/Unix command line.
You have the run_shell_command tool to execute any commands: ls, grep, find, cat, ps, df, etc.

SECURITY RULES - CRITICAL:
- NEVER install any software, packages, or tools without explicit user permission
- NEVER use commands like: apt install, yum install, brew install, pip install, npm install, cargo install, etc.
- If a task requires software that may not be installed, ASK the user first: "To complete this task, I need to install [tool name]. May I proceed with installation?"
- Wait for user confirmation before proceeding with any installation
- Do not assume tools are available - check first with commands like 'which [tool]' or '[tool] --version'
- If a required tool is missing, explain what's needed and ask permission to install

EXECUTION STRATEGY:
1. Determine which commands need to be executed to fulfill the user's request
2. Check if required tools are available (use 'which' or '--version' commands)
3. If tools are missing and installation is needed, you may install it after getting user agreement
4. Execute them using run_shell_command tool only after confirming tools are available
5. Analyze the command results carefully:
   - If the command succeeded and provides useful information → proceed to next step or provide final answer
   - If the command failed or output is unclear → try a different approach or modify the command
   - If you need more specific information → execute additional commands
6. You can execute multiple commands in sequence, but be strategic about it
7. If a command doesn't work as expected, you may retry with modifications up to 2-3 times
8. Once you have sufficient information to answer the user's question, provide a clear response and STOP calling tools

IMPORTANT COMPLETION RULES:
- ALWAYS show the actual command output to the user in your final response
- When you receive command results, include the actual output/data in your response to the user
- Do not just say "command executed successfully" - show the real results
- Do not continue calling tools indefinitely - stop when you have enough data to answer
- If after 2-3 attempts a command still doesn't work, explain what went wrong and suggest alternatives
- Respond in the same language as the user's prompt
- Keep original command output format unless explicitly asked to format it differently
- Be concise but informative in your final answer"""


class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    GEMINI = "gemini"


# Global configuration for models by provider
PROVIDER_MODELS = {
    LLMProvider.OPENAI: "gpt-4o-mini",
    LLMProvider.GEMINI: "gemini-2.0-flash-exp",
}


def set_model_for_provider(provider: LLMProvider, model_name: str) -> None:
    """Set the model name for a specific provider."""
    PROVIDER_MODELS[provider] = model_name


def get_model_for_provider(provider: LLMProvider) -> str:
    """Get the model name for a specific provider."""
    return PROVIDER_MODELS[provider]


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute specified tool with given arguments."""
    if tool_name == "run_shell_command":
        command = arguments.get("command", "")
        if not command:
            return {"success": False, "error": "Command not specified"}

        try:
            # Execute command through shell
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout for security
            )

            return {"success": True, "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode, "command": command}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command execution timeout exceeded (30 sec)"}
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


def get_display_name(provider: LLMProvider) -> str:
    """Get display name for the specified provider."""
    return GET_DISPLAY_NAME[provider.value]()


def process_user_message(
    user_prompt: str,
    provider: LLMProvider,
    client_or_model: Any,
    history: Dict[str, Any] | None = None,
    return_usage: bool = False,
    verbose: bool = False,
) -> Union[str, Tuple[str, Dict[str, Any]]]:
    """Process user message through the specified provider using unified agent loop."""

    # Include history context if available
    full_prompt = user_prompt
    if history and history["lines"]:
        history_text = format_history_for_prompt(history)
        full_prompt = f"{history_text}\nUser: {user_prompt}"

    try:
        max_iterations = 5
        iteration = 0
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # Provider-specific initialization
        from openai.types.chat import ChatCompletionMessageParam

        messages: List[ChatCompletionMessageParam] = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": full_prompt}]

        if provider not in [LLMProvider.OPENAI, LLMProvider.GEMINI]:
            raise ValueError(f"Unsupported provider: {provider}")

        # Main agent loop
        while iteration < max_iterations:
            iteration += 1
            if verbose:
                print(f"[DEBUG] Iteration {iteration}/{max_iterations}")

            # Send message to provider
            response = SEND_MESSAGE[provider.value](client_or_model, messages)

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

                    result = execute_tool(function_name, function_args)
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


def main(verbose: bool = False, provider: str = "openai", model: str = None) -> None:
    """Main function for interactive agent communication.

    Args:
        verbose: Show detailed token usage information
        provider: LLM provider to use ("openai" or "gemini")
        model: Model name to use for the selected provider (optional)
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
        else:
            print(f"Error: Unsupported provider '{provider}'. Use 'openai' or 'gemini'.")
            return

        client_or_model = initialize_client(llm_provider)
        current_model = get_model_for_provider(llm_provider)
        print(f"Using {get_display_name(llm_provider)} - Model: {current_model}")

    except ValueError as e:
        print(f"Error: {e}")
        return

    # Initialize chat history
    chat_history = {"lines": [], "total_tokens": 0}

    while True:
        try:
            user_input = input("\nUser: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            if not user_input:
                continue

            print("Agent is analyzing request...")
            add_to_history(chat_history, f"User: {user_input}")

            if verbose:
                response, usage_info = process_user_message(user_input, llm_provider, client_or_model, chat_history, return_usage=True, verbose=True)
            else:
                response = process_user_message(user_input, llm_provider, client_or_model, chat_history, return_usage=False, verbose=False)

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


if __name__ == "__main__":
    main()
