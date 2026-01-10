from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from shlex import quote
from typing import Dict, List, Sequence

from agent.config import AppConfig
from agent.history import HistoryStore
from agent.llm_client import LLMClientError, LLMResponse, complete_chat
from agent.tools import TOOL_DEFINITIONS, execute_tool_call, get_active_workdir, get_initial_workdir
from agent.ui import status
from agent.utils import BuiltinCommand, parse_builtin_command
from rich.markdown import Markdown


@dataclass
class AgentResult:
    exit_code: int
    add_lines: List[str]


async def run_agent(
    user_request: str,
    config: AppConfig,
    history: HistoryStore,
    console,
    builtin_command: BuiltinCommand | None = None,
) -> AgentResult:
    messages: List[Dict[str, object]] = []

    active_builtin = builtin_command
    if active_builtin is None:
        active_builtin, _ = parse_builtin_command(user_request)

    if active_builtin == BuiltinCommand.RESET_SESSION:
        history.reset()
        console.print("✅ reset")
        return AgentResult(exit_code=0, add_lines=[])

    system_prompt = config.prompt.system_prompt.strip()
    custom_prompt = config.prompt.custom_prompt.strip()

    if system_prompt:
        system_message = {"role": "system", "content": system_prompt}
        if custom_prompt and config.prompt.custom_prompt_mode == "system":
            system_message["content"] = f"{system_prompt.rstrip()}\n\n{custom_prompt}"
            custom_prompt = ""
        messages.append(system_message)

    if custom_prompt:
        prompt_role = "developer" if config.prompt.custom_prompt_mode == "developer" else "system"
        messages.append({"role": prompt_role, "content": custom_prompt})

    history_messages = history.load_chat_messages()
    messages.extend(history_messages)

    history.append_nl_command(user_request)
    user_message = {"role": "user", "content": user_request}
    messages.append(user_message)
    history.append_chat(user_message)

    for step in range(1, config.agent.max_steps + 1):
        try:
            with status(console, config.ui.rich, "Waiting for LLM response..."):
                llm_response = await asyncio.wait_for(
                    complete_chat(messages, TOOL_DEFINITIONS, config.provider),
                    timeout=config.agent.timeout_sec,
                )
        except asyncio.TimeoutError:
            console.print("LLM request timed out.")
            return AgentResult(exit_code=1, add_lines=[])
        except LLMClientError as exc:
            console.print(f"LLM error: {exc}")
            return AgentResult(exit_code=1, add_lines=[])

        assistant_message = llm_response.message
        messages.append(assistant_message)
        history.append_chat(assistant_message)

        tool_calls: Sequence[Dict] = assistant_message.get("tool_calls") or []
        if tool_calls:
            limited_calls = list(tool_calls)[: config.agent.max_tool_calls_per_step]
            if len(tool_calls) > len(limited_calls):
                console.print(f"Truncated tool calls to {config.agent.max_tool_calls_per_step}.")
            for call in limited_calls:
                name = call.get("function", {}).get("name", "unknown")
                args_preview = call.get("function", {}).get("arguments", "")
                prefix = f"[{step}/{config.agent.max_steps}] "
                if config.ui.show_tool_args:
                    console.print(f"{prefix}→ {name}({args_preview})")
                else:
                    console.print(f"{prefix}→ {name}()")

                result = await execute_tool_call(call)
                tool_message = {
                    "role": "tool",
                    "tool_call_id": call.get("id"),
                    "name": name,
                    "content": result,
                }
                messages.append(tool_message)
                history.append_chat(tool_message)
                console.print("✓ done")
            continue

        content_value = assistant_message.get("content") or ""
        if isinstance(content_value, list):
            content_value = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in content_value
            )
        elif not isinstance(content_value, str):
            content_value = str(content_value)

        final_text = content_value
        add_lines = [line for line in final_text.splitlines() if line.strip().startswith("ADD ")]
        human_lines = [line for line in final_text.splitlines() if not line.strip().startswith("ADD ")]

        if human_lines and config.ui.show_step_summary:
            human_text = "\n".join(human_lines)
            if config.ui.rich and config.ui.render_markdown:
                console.print(Markdown(human_text))
            else:
                console.print(human_text)

        if config.agent.follow_cwd:
            active_cwd = get_active_workdir()
            initial_cwd = get_initial_workdir()
            has_cd = any(line.strip().startswith("ADD cd ") for line in add_lines)
            if active_cwd and initial_cwd and active_cwd != initial_cwd and not has_cd:
                add_lines.append(f"ADD cd {quote(str(active_cwd))}")

        for line in add_lines:
            print(line, file=sys.stdout)
        return AgentResult(exit_code=0, add_lines=add_lines)

    console.print("Reached max steps without a final response.")
    return AgentResult(exit_code=1, add_lines=[])
