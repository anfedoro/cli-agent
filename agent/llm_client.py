from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List

from openai import AsyncOpenAI

from agent.config import ProviderConfig


class LLMClientError(Exception):
    """Raised when the LLM client fails to produce a response."""


@dataclass
class LLMResponse:
    message: Dict[str, Any]
    finish_reason: str


def _build_client(provider: ProviderConfig) -> AsyncOpenAI:
    api_key = os.getenv(provider.api_key_env)
    if not api_key:
        raise LLMClientError(f"Missing API key in environment variable {provider.api_key_env}")
    return AsyncOpenAI(api_key=api_key, base_url=provider.base_url or None)


async def complete_chat(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    provider: ProviderConfig,
) -> LLMResponse:
    client = _build_client(provider)
    try:
        response = await client.chat.completions.create(
            model=provider.model,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
            **provider.model_params,
        )
    except Exception as exc:
        raise LLMClientError(f"LLM request failed: {exc}") from exc

    if not response.choices:
        raise LLMClientError("LLM returned no choices")

    choice = response.choices[0]
    message_payload = choice.message
    if hasattr(message_payload, "model_dump"):
        message_dict: Dict[str, Any] = message_payload.model_dump()
    else:
        message_dict = message_payload  # type: ignore[assignment]
    return LLMResponse(message=message_dict, finish_reason=choice.finish_reason or "")
