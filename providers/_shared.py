"""Shared helpers for provider send_message consistency.

This module centralizes construction of parameters for OpenAI-compatible chat completion
calls so that all providers (openai, gemini, lmstudio) follow the same internal logic
while still handling provider-specific parameter differences.
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, Union

from openai import APIError, BadRequestError
from openai.types.chat import ChatCompletionMessageParam

# Default unified limits
_DEFAULT_MAX_TOKENS = 4096


def extract_unsupported_parameter(error: Union[Exception, str]) -> Optional[str]:
    """Extract the name of unsupported parameter from API error.

    Args:
        error: Exception object or error message string

    Returns:
        Parameter name if found, None otherwise
    """
    # Handle OpenAI APIError exceptions
    if isinstance(error, APIError):
        if hasattr(error, "body") and error.body:
            try:
                body = error.body
                if isinstance(body, dict) and "error" in body:
                    error_info = body["error"]

                    # Case 1: Known parameter with invalid value (param field populated)
                    # Case 2: Known parameter unsupported by model (param field populated)
                    if "param" in error_info and error_info["param"]:
                        return error_info["param"]

                    # Case 3: Completely unrecognized parameter (param is null, extract from message)
                    message = error_info.get("message", "")
                    if "Unrecognized request argument supplied:" in message:
                        # Format: "Unrecognized request argument supplied: parameter_name"
                        parts = message.split(":")
                        if len(parts) > 1:
                            param_name = parts[1].strip()
                            return param_name
            except Exception:
                pass

    # Handle string errors that might contain JSON
    error_str = str(error)
    try:
        # Try to parse JSON from error string
        if "{" in error_str and "}" in error_str:
            json_start = error_str.find("{")
            json_end = error_str.rfind("}") + 1
            json_part = error_str[json_start:json_end]
            error_data = json.loads(json_part)

            if "error" in error_data:
                error_info = error_data["error"]

                # Check param field first (covers invalid_value and unknown_parameter cases)
                if "param" in error_info and error_info["param"]:
                    return error_info["param"]

                # Check for completely unrecognized parameter in message
                message = error_info.get("message", "")
                if "Unrecognized request argument supplied:" in message:
                    parts = message.split(":")
                    if len(parts) > 1:
                        param_name = parts[1].strip()
                        return param_name
    except (json.JSONDecodeError, KeyError):
        pass

    return None


def is_parameter_error(error: Union[Exception, str]) -> bool:
    """Check if error is related to unsupported parameters.

    Args:
        error: Exception object or error message string

    Returns:
        True if this appears to be a parameter-related error
    """
    # Handle OpenAI structured errors
    if isinstance(error, (APIError, BadRequestError)):
        if hasattr(error, "body") and error.body:
            try:
                body = error.body
                if isinstance(body, dict) and "error" in body:
                    error_info = body["error"]
                    error_type = error_info.get("type", "")
                    message = error_info.get("message", "")
                    code = error_info.get("code", "")

                    # Check if it's invalid_request_error with parameter-related codes
                    if error_type == "invalid_request_error":
                        # Case 1: Invalid parameter value (e.g., temperature > 2.0)
                        if code in ["invalid_value", "decimal_above_max_value"]:
                            return True
                        # Case 2: Known parameter unsupported by model
                        if code == "unknown_parameter":
                            return True
                        # Case 3: Completely unrecognized parameter
                        if "Unrecognized request argument supplied:" in message:
                            return True
                        # Case 4: Any error with param field populated
                        if error_info.get("param") is not None:
                            return True
            except Exception:
                pass
        return True  # Assume APIError/BadRequestError are parameter-related

    # Check if it's an HTTP error with relevant status codes
    if hasattr(error, "status_code"):
        status_code = getattr(error, "status_code")
        if status_code in [400, 422]:
            return True

    # Handle string errors that might contain JSON
    error_str = str(error)
    try:
        if "{" in error_str and "}" in error_str:
            json_start = error_str.find("{")
            json_end = error_str.rfind("}") + 1
            json_part = error_str[json_start:json_end]
            error_data = json.loads(json_part)

            if "error" in error_data:
                error_info = error_data["error"]
                error_type = error_info.get("type", "")
                message = error_info.get("message", "")
                code = error_info.get("code", "")

                if error_type == "invalid_request_error":
                    # Check parameter-related codes and messages
                    if code in ["invalid_value", "decimal_above_max_value", "unknown_parameter"]:
                        return True
                    if "Unrecognized request argument supplied:" in message:
                        return True
                    if error_info.get("param") is not None:
                        return True
    except (json.JSONDecodeError, KeyError):
        pass

    return False


def prepare_chat_completion_params(provider: str, model: str, messages: List[ChatCompletionMessageParam], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Prepare kwargs for client.chat.completions.create.

    Unifies logic across providers while respecting subtle API differences.

    Rules:
    - Always include model, messages, tools, tool_choice="auto".
    - For lmstudio (local server) use `max_tokens` (widely supported keyword)
      because some local OpenAI-compatible servers ignore / reject `max_completion_tokens`.
    - For cloud providers (openai, gemini) prefer `max_completion_tokens` and include
      a gentle `reasoning_effort` hint where supported (OpenAI currently supports it; if
      a provider ignores it, it's harmless).
    """
    base: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "reasoning_effort": "low",  # for reasoning models like o1-mini
    }

    if provider == "lmstudio":
        base["max_tokens"] = _DEFAULT_MAX_TOKENS

    else:
        base["max_completion_tokens"] = _DEFAULT_MAX_TOKENS

    return base
