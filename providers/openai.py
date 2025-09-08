import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from ._shared import prepare_chat_completion_params, extract_unsupported_parameter, is_parameter_error
from agent.utils import get_llm_timeout_seconds

# Load environment variables
load_dotenv()


def get_available_tools() -> List[Dict[str, Any]]:
    """Return available tool definitions for OpenAI API."""
    from agent.core_agent import get_agent_tools

    return get_agent_tools()


def initialize_client() -> OpenAI:
    """Initialize OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not found.")
    timeout = get_llm_timeout_seconds()
    return OpenAI(api_key=api_key, timeout=timeout)


def get_display_name(model_name: str) -> str:
    """Get the display name for OpenAI with the specified model."""
    return f"OpenAI - Model: {model_name}"


def send_message(client: OpenAI, messages: List[ChatCompletionMessageParam], model_name: str) -> Any:
    """Send message to OpenAI API with error handling for unsupported parameters."""
    params = prepare_chat_completion_params("openai", model_name, messages, get_available_tools())

    try:
        return client.chat.completions.create(**params)
    except Exception as e:
        # Check if error is about unsupported parameter
        if is_parameter_error(e):
            unsupported_param = extract_unsupported_parameter(e)
            if unsupported_param and unsupported_param in params:
                # Remove unsupported parameter and retry
                params_retry = params.copy()
                del params_retry[unsupported_param]

                try:
                    return client.chat.completions.create(**params_retry)
                except Exception:
                    # If retry also fails, raise the original error
                    raise e

        # For other errors or if we couldn't identify the parameter, raise immediately
        raise e


def extract_function_calls(response) -> List[Dict[str, Any]]:
    """Extract function calls from OpenAI response."""
    function_calls = []
    message = response.choices[0].message

    if hasattr(message, "tool_calls") and message.tool_calls:
        for tool_call in message.tool_calls:
            function_calls.append({"id": tool_call.id, "name": tool_call.function.name, "arguments": json.loads(tool_call.function.arguments)})

    return function_calls


def add_function_result_to_messages(messages: List[ChatCompletionMessageParam], response, function_results: List[Dict[str, Any]]) -> None:
    """Add function execution results to message history."""
    message = response.choices[0].message

    # Add assistant message with tool calls
    messages.append({"role": "assistant", "content": message.content or "", "tool_calls": message.tool_calls})

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
    """Extract token usage information from OpenAI response."""
    if hasattr(response, "usage") and response.usage:
        usage = response.usage
        return {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def get_response_text(response) -> str:
    """Extract response text from OpenAI response."""
    message = response.choices[0].message
    return message.content or ""
