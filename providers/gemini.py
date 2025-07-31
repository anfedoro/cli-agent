import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

# Load environment variables
load_dotenv()


def get_available_tools() -> List[Dict[str, Any]]:
    """Return available tool definitions for Gemini API using OpenAI format."""
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


def initialize_client() -> OpenAI:
    """Initialize Gemini client using OpenAI-compatible API."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not found.")

    # Use Google's OpenAI-compatible endpoint
    return OpenAI(api_key=api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")


def get_model_name() -> str:
    """Get the model name for Gemini."""
    return "gemini-2.0-flash-exp"


def get_display_name() -> str:
    """Get the display name for Gemini."""
    return "Google Gemini 2.0 Flash (OpenAI API)"


def send_message(client: OpenAI, messages: List[ChatCompletionMessageParam], model_name: str = None) -> Any:
    """Send message to Gemini API using OpenAI format."""
    model_to_use = model_name if model_name else get_model_name()
    return client.chat.completions.create(model=model_to_use, messages=messages, tools=get_available_tools(), tool_choice="auto")


def extract_function_calls(response) -> List[Dict[str, Any]]:
    """Extract function calls from Gemini response using OpenAI format."""
    function_calls = []
    message = response.choices[0].message

    if hasattr(message, "tool_calls") and message.tool_calls:
        for tool_call in message.tool_calls:
            function_calls.append({"id": tool_call.id, "name": tool_call.function.name, "arguments": json.loads(tool_call.function.arguments)})

    return function_calls


def add_function_result_to_messages(messages: List[ChatCompletionMessageParam], response, function_results: List[Dict[str, Any]]) -> None:
    """Add function execution results to message history using OpenAI format."""
    message = response.choices[0].message

    # Add assistant message with tool calls
    messages.append({"role": "assistant", "content": message.content or "", "tool_calls": message.tool_calls})

    # Add tool execution results
    for i, result in enumerate(function_results):
        tool_call = message.tool_calls[i]
        messages.append({"tool_call_id": tool_call.id, "role": "tool", "name": tool_call.function.name, "content": json.dumps(result, ensure_ascii=False)})


def extract_usage_info(response) -> Dict[str, int]:
    """Extract token usage information from Gemini response using OpenAI format."""
    if hasattr(response, "usage") and response.usage:
        usage = response.usage
        return {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def get_response_text(response) -> str:
    """Extract response text from Gemini response using OpenAI format."""
    message = response.choices[0].message
    return message.content or ""
