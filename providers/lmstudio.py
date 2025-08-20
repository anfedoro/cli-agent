import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from ._shared import prepare_chat_completion_params

# Load environment variables
load_dotenv()

# Global configuration for reasoning
_no_reasoning = False


def set_no_reasoning(value: bool):
    """Set global no_reasoning configuration."""
    global _no_reasoning
    _no_reasoning = value


def is_no_reasoning() -> bool:
    """Check if reasoning is disabled globally."""
    return _no_reasoning


def get_available_tools() -> List[Dict[str, Any]]:
    """Return available tool definitions for LM Studio API using OpenAI format."""
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
        }
    ]


def initialize_client() -> OpenAI:
    """Initialize LM Studio client using OpenAI-compatible API."""
    # LM Studio default base URL
    base_url = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    # API key is not required for LM Studio but we use a placeholder
    api_key = os.getenv("LM_STUDIO_API_KEY", "lm-studio")

    return OpenAI(api_key=api_key, base_url=base_url)


def get_model_name() -> str:
    """Get the default model name for LM Studio."""
    # This should be overridden by the user-specified model
    return "lmstudio-community/qwen2.5-7b-instruct"


def get_display_name(model_name: str) -> str:
    """Get the display name for LM Studio with the specified model."""
    return f"LM Studio - Model: {model_name}"


def send_message(client: OpenAI, messages: List[ChatCompletionMessageParam], model_name: Optional[str] = None) -> Any:
    """Send message to LM Studio API (unified logic)."""
    model_to_use = model_name or get_model_name()
    params = prepare_chat_completion_params("lmstudio", model_to_use, messages, get_available_tools())
    # Potential future reasoning flags could be injected here based on _no_reasoning
    return client.chat.completions.create(**params)  # type: ignore


def extract_function_calls(response) -> List[Dict[str, Any]]:
    """Extract function calls from LM Studio response using OpenAI format."""
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
    assistant_message: ChatCompletionMessageParam = {"role": "assistant", "content": message.content or "", "tool_calls": message.tool_calls}
    messages.append(assistant_message)

    # Add tool execution results
    for i, result in enumerate(function_results):
        tool_call = message.tool_calls[i]
        tool_message: ChatCompletionMessageParam = {  # type: ignore
            "tool_call_id": tool_call.id,
            "role": "tool",
            "name": tool_call.function.name,
            "content": json.dumps(result, ensure_ascii=False),
        }
        messages.append(tool_message)


def extract_usage_info(response) -> Dict[str, int]:
    """Extract token usage information from LM Studio response using OpenAI format."""
    if hasattr(response, "usage") and response.usage:
        usage = response.usage
        return {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def get_response_text(response) -> str:
    """Extract response text from LM Studio response using OpenAI format."""
    message = response.choices[0].message
    return message.content or ""
