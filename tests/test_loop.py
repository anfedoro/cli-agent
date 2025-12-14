import pytest

from agent import loop as loop_module
from agent.config import AgentConfig, AppConfig, PromptConfig, ProviderConfig, UIConfig
from agent.history import HistoryStore
from agent.llm_client import LLMResponse
from agent.loop import run_agent
from agent.ui import build_console


@pytest.mark.asyncio
async def test_loop_runs_tool_and_outputs_add(monkeypatch, capsys, tmp_path):
    async def fake_complete(messages, tools, provider):
        # If a tool result is already present, return a final answer.
        if any(m.get("role") == "tool" for m in messages):
            return LLMResponse(
                message={"role": "assistant", "content": "ADD echo hi\nFinished"},
                finish_reason="stop",
            )
        return LLMResponse(
            message={
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {"name": "read_file", "arguments": '{"path": "README.md"}'},
                    }
                ],
            },
            finish_reason="tool_calls",
        )

    async def fake_execute_tool_call(tool_call):
        return "ok"

    monkeypatch.setattr(loop_module, "complete_chat", fake_complete)
    monkeypatch.setattr(loop_module, "execute_tool_call", fake_execute_tool_call)

    config = AppConfig(
        provider=ProviderConfig(api_key_env="DUMMY"),
        agent=AgentConfig(max_steps=3, timeout_sec=2, history_dir=tmp_path, session="demo"),
        ui=UIConfig(rich=False, show_tool_args=True, show_step_summary=True),
        tools={},
    )
    history = HistoryStore(tmp_path, "demo")
    console = build_console(False)

    result = await run_agent("Do something", config, history, console)

    captured = capsys.readouterr()
    assert result.exit_code == 0
    assert "ADD echo hi" in captured.out
    assert "Finished" in captured.err
    assert "[1/3] → read_file" in captured.err


@pytest.mark.asyncio
async def test_loop_injects_system_and_custom_prompts(monkeypatch, tmp_path):
    seen_messages = []

    async def fake_complete(messages, tools, provider):
        seen_messages.extend(messages)
        return LLMResponse(message={"role": "assistant", "content": "done"}, finish_reason="stop")

    monkeypatch.setattr(loop_module, "complete_chat", fake_complete)

    config = AppConfig(
        provider=ProviderConfig(api_key_env="DUMMY"),
        agent=AgentConfig(max_steps=1, timeout_sec=2, history_dir=tmp_path, session="demo"),
        prompt=PromptConfig(system_prompt="SYSTEM", custom_prompt="CUSTOM", custom_prompt_mode="developer"),
        ui=UIConfig(rich=False),
        tools={},
    )
    history = HistoryStore(tmp_path, "demo")
    console = build_console(False)

    await run_agent("Hi", config, history, console)

    assert seen_messages[0] == {"role": "system", "content": "SYSTEM"}
    assert seen_messages[1] == {"role": "developer", "content": "CUSTOM"}
    assert seen_messages[-1]["role"] == "user"
    assert seen_messages[-1]["content"] == "Hi"


@pytest.mark.asyncio
async def test_loop_hides_step_when_no_tools(monkeypatch, capsys, tmp_path):
    async def fake_complete(messages, tools, provider):
        return LLMResponse(message={"role": "assistant", "content": "just text"}, finish_reason="stop")

    monkeypatch.setattr(loop_module, "complete_chat", fake_complete)

    config = AppConfig(
        provider=ProviderConfig(api_key_env="DUMMY"),
        agent=AgentConfig(max_steps=1, timeout_sec=2, history_dir=tmp_path, session="demo"),
        prompt=PromptConfig(),
        ui=UIConfig(rich=False),
        tools={},
    )
    history = HistoryStore(tmp_path, "demo")
    console = build_console(False)

    await run_agent("Hi", config, history, console)

    captured = capsys.readouterr()
    assert "Step 1/" not in captured.err
    assert "just text" in captured.err


@pytest.mark.asyncio
async def test_loop_handles_reset_without_llm(monkeypatch, tmp_path):
    called = {"llm": False}

    async def fake_complete(messages, tools, provider):
        called["llm"] = True
        return LLMResponse(message={"role": "assistant", "content": "should not run"}, finish_reason="stop")

    monkeypatch.setattr(loop_module, "complete_chat", fake_complete)

    config = AppConfig(
        provider=ProviderConfig(api_key_env="DUMMY"),
        agent=AgentConfig(max_steps=1, timeout_sec=2, history_dir=tmp_path, session="demo"),
        prompt=PromptConfig(),
        ui=UIConfig(rich=False),
        tools={},
    )
    history = HistoryStore(tmp_path, "demo")
    console = build_console(False)

    result = await run_agent("/reset", config, history, console)

    assert result.exit_code == 0
    assert called["llm"] is False
    assert history.chat_path.read_text(encoding="utf-8") == ""
