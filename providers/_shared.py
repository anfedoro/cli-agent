"""Shared helpers for provider send_message consistency.

This module centralizes construction of parameters for OpenAI-compatible chat completion
calls so that all providers (openai, gemini, lmstudio) follow the same internal logic
while still handling provider-specific parameter differences.
"""

from __future__ import annotations
from typing import Any, Dict, List
from openai.types.chat import ChatCompletionMessageParam

# Default unified limits
_DEFAULT_MAX_TOKENS = 4096


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
        "reasoning_effort": "low",  # if unsupported, server should ignore
    }

    if provider == "lmstudio":
        base["max_tokens"] = _DEFAULT_MAX_TOKENS

    else:
        base["max_completion_tokens"] = _DEFAULT_MAX_TOKENS

    return base
