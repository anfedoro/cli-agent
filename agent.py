import json
import os
import subprocess
from typing import Any, Dict, List, Tuple, Union

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

# Load environment variables from .env file
load_dotenv()

# Configuration constants for history management
MAX_CONTEXT_TOKENS = 4000
HISTORY_TRIM_LINES = 5


def get_available_tools() -> List[ChatCompletionToolParam]:
    """Return available tool definitions for OpenAI API function calling."""
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
                            "description": "Shell command to execute, e.g. 'ls -la /tmp' or 'grep -r \"pattern\" .'",
                        }
                    },
                    "required": ["command"],
                },
            },
        }
    ]


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


def process_user_message(
    user_prompt: str, client: OpenAI, history: Dict[str, Any] | None = None, return_usage: bool = False
) -> Union[str, Tuple[str, Dict[str, Any]]]:
    """
    Process user message through OpenAI API.
    Supports multi-step command execution and history management.

    Args:
        user_prompt: User's message
        client: OpenAI client instance
        history: Chat history dictionary
        return_usage: If True, return tuple (response, usage_info)

    Returns:
        str or tuple: Response text, or (response_text, usage_info) if return_usage=True
    """

    # Prepare system prompt with history context
    system_prompt = """You are a terminal agent with access to Linux/Unix command line.
You have the run_shell_command tool to execute any commands: ls, grep, find, cat, ps, df, etc.

EXECUTION STRATEGY:
1. Determine which commands need to be executed to fulfill the user's request
2. Execute them using run_shell_command tool
3. Analyze the command results carefully:
   - If the command succeeded and provides useful information → proceed to next step or provide final answer
   - If the command failed or output is unclear → try a different approach or modify the command
   - If you need more specific information → execute additional commands
4. You can execute multiple commands in sequence, but be strategic about it
5. If a command doesn't work as expected, you may retry with modifications up to 2-3 times
6. Once you have sufficient information to answer the user's question, provide a clear response and STOP calling tools

IMPORTANT COMPLETION RULES:
- Always provide a final text response to the user after gathering necessary information
- Do not continue calling tools indefinitely - stop when you have enough data to answer
- If after 2-3 attempts a command still doesn't work, explain what went wrong and suggest alternatives
- Respond in the same language as the user's prompt
- try to keep original comman output format until it explicitly asked to format it in certain way
- Be concise but informative in your final answer"""

    # Include history context if available
    full_prompt = user_prompt
    if history and history["lines"]:
        history_text = format_history_for_prompt(history)
        full_prompt = f"{history_text}\nUser: {user_prompt}"

    messages: List[ChatCompletionMessageParam] = [{"role": "system", "content": system_prompt}, {"role": "user", "content": full_prompt}]

    try:
        # Command execution loop - model can execute multiple commands in sequence
        max_iterations = 5  # Limit iterations for security
        iteration = 0
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        while iteration < max_iterations:
            iteration += 1
            print(f"[DEBUG] Iteration {iteration}/{max_iterations}")

            response = client.chat.completions.create(model="gpt-4.1-mini", messages=messages, tools=get_available_tools(), tool_choice="auto")

            # Update token usage in history and collect usage stats
            if hasattr(response, "usage") and response.usage:
                usage = response.usage
                total_usage["prompt_tokens"] += usage.prompt_tokens
                total_usage["completion_tokens"] += usage.completion_tokens
                total_usage["total_tokens"] += usage.total_tokens

                if history is not None:
                    history["total_tokens"] += usage.total_tokens
                    # Trim history if too many tokens
                    if history["total_tokens"] > MAX_CONTEXT_TOKENS:
                        trim_history_lines(history)

            message = response.choices[0].message

            # If there are tool calls - execute them
            if hasattr(message, "tool_calls") and message.tool_calls:
                # Add assistant message
                messages.append({"role": "assistant", "content": message.content or "", "tool_calls": message.tool_calls})  # type: ignore

                # Execute each tool
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    # Log command execution for debugging
                    command = function_args.get("command", "N/A")
                    _log_command_execution(command)

                    result = execute_tool(function_name, function_args)

                    # Add tool execution result
                    messages.append({"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": json.dumps(result, ensure_ascii=False)})  # type: ignore

                # Continue loop - model may want to execute more commands
                print("[DEBUG] Tool execution completed, continuing loop")
                continue
            else:
                # No tools - return final answer
                print("[DEBUG] No more tools to execute, returning final answer")
                content = message.content or ""
                if return_usage:
                    return content, total_usage
                return content

        error_msg = "Maximum iterations reached. Please try to simplify your request."
        return (error_msg, total_usage) if return_usage else error_msg

    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        return (error_msg, {}) if return_usage else error_msg


def _log_command_execution(command: str) -> None:
    """Log command execution for debugging purposes."""
    print(f"Executing command: {command}")


def main(verbose: bool = False) -> None:
    """Main function for interactive agent communication.

    Args:
        verbose: Show detailed token usage information
    """
    print("LLM Terminal Agent started!")
    print("You can ask to execute any Linux commands: ls, grep, find, ps, etc.")
    print("To exit type: quit, exit, or q")
    print("-" * 50)

    # Initialize OpenAI client
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("Error: OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        return

    client = OpenAI(api_key=openai_api_key)

    # Initialize chat history as dictionary
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
                response, usage_info = process_user_message(user_input, client, chat_history, return_usage=True)
            else:
                response = process_user_message(user_input, client, chat_history)

            add_to_history(chat_history, f"Agent: {response}")
            print(f"\nAgent: {response}")

            # Show detailed token usage in verbose mode
            if verbose:
                try:
                    response, usage_info = locals()["response"], locals()["usage_info"]
                    if usage_info:
                        print(
                            f"\n[Token Usage] Prompt: {usage_info.get('prompt_tokens', 0)}, Completion: {usage_info.get('completion_tokens', 0)}, Total: {usage_info.get('total_tokens', 0)}"
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
