"""Shared helpers for provider send_message consistency.

This module centralizes construction of parameters for OpenAI-compatible chat completion
calls so that all providers (openai, gemini, lmstudio) follow the same internal logic
while still handling provider-specific parameter differences.
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, Union
import re
import os

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


def _get_reasoning_model_patterns(provider: str) -> List[str]:
    """Get reasoning model patterns from ENV/config with sensible defaults per provider.

    - ENV can override via CLI_AGENT_REASONING_MODELS or CLI_AGENT_REASONING_MODELS_<PROVIDER>
    - Config can override via `reasoning_model_patterns` mapping {provider: [patterns]}
    - Patterns are treated as regex (case-insensitive). If plain text is given, it's used as substring regex.
    """
    patterns: List[str] = []

    # Provider-specific env override
    per_provider_env = os.getenv(f"CLI_AGENT_REASONING_MODELS_{provider.upper()}")
    if per_provider_env:
        patterns.extend([p.strip() for p in per_provider_env.split(",") if p.strip()])

    # Global env fallback
    global_env = os.getenv("CLI_AGENT_REASONING_MODELS")
    if global_env:
        patterns.extend([p.strip() for p in global_env.split(",") if p.strip()])

    # Config mapping
    try:
        from agent.config import get_setting

        cfg_map = get_setting("reasoning_model_patterns", None)
        if isinstance(cfg_map, dict):
            extra = cfg_map.get(provider)
            if isinstance(extra, list):
                patterns.extend([str(p) for p in extra])
    except Exception:
        pass

    # Sensible defaults per provider
    if not patterns:
        if provider == "openai":
            patterns = [
                r"^o\d+.*",  # o-series like o1, o3, etc.
                r"^gpt-5(\b|-)",  # gpt-5 family, e.g., gpt-5, gpt-5-mini
                r"^gpt-4o-reasoning\b",  # explicit 4o reasoning variants
                r"^gpt-o\b",  # gpt-o family
            ]
        elif provider == "gemini":
            # Broadly treat *pro* variants as reasoning-capable (user request)
            patterns = [r"gemini.*pro"]
        else:
            patterns = []

    return patterns


def _is_reasoning_model(provider: str, model: str) -> bool:
    """Detect reasoning models using provider-aware pattern lists."""
    if not model:
        return False
    patterns = _get_reasoning_model_patterns(provider)
    m = model.lower()
    for pat in patterns:
        try:
            # If pattern looks like a bare word, treat as substring, else regex
            regex = pat
            # Allow simple wildcard '*'
            if "*" in regex:
                regex = regex.replace("*", ".*")
            if re.search(regex, m, re.IGNORECASE):
                return True
        except re.error:
            # Fallback to substring match if regex is invalid
            if pat.lower() in m:
                return True
    return False


def _apply_generation_settings(params: Dict[str, Any], provider: str, model: str) -> None:
    """Apply configurable generation settings safely based on model capabilities."""
    try:
        from agent.config import get_setting
    except Exception:
        return

    is_reasoning = _is_reasoning_model(provider, model)

    # Temperature: exclude for reasoning models; include for others if set
    temperature = get_setting("temperature", None)
    if temperature is not None and not is_reasoning:
        try:
            t = float(temperature)
            if 0.0 <= t <= 2.0:
                params["temperature"] = t
        except Exception:
            pass

    # Reasoning effort: include only for reasoning models (and only for OpenAI for now)
    reasoning_effort = get_setting("reasoning_effort", None)
    if is_reasoning and provider == "openai" and isinstance(reasoning_effort, str) and reasoning_effort:
        params["reasoning_effort"] = reasoning_effort

    # Reasoning verbosity (optional): include only for reasoning models if explicitly set
    reasoning_verbosity = get_setting("reasoning_verbosity", None)
    if is_reasoning and provider == "openai" and isinstance(reasoning_verbosity, str) and reasoning_verbosity:
        # Use a conservative key; if unsupported, providers/openai retry logic will drop it
        params["reasoning_verbosity"] = reasoning_verbosity


def prepare_chat_completion_params(provider: str, model: str, messages: List[ChatCompletionMessageParam], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Prepare kwargs for client.chat.completions.create.

    Use only parameters compatible with OpenAI Chat Completions API and most
    OpenAI-compatible servers:
    - model, messages, tools, tool_choice="auto"
    - max_completion_tokens (not max_tokens)
    - Do NOT include experimental parameters like reasoning_effort by default
    """
    base: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "max_completion_tokens": _DEFAULT_MAX_TOKENS,
    }
    # Apply model-aware generation parameters and config-driven knobs
    _apply_generation_settings(base, provider, model)
    return base
