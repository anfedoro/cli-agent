from pathlib import Path

import tomllib

import pytest

from agent.tools import execute_tool_call, set_active_config_path


@pytest.mark.asyncio
async def test_show_and_set_config(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        """
[provider]
name = "openai"
model = "gpt-default"

[provider.model_params]
temperature = 0.1
""",
        encoding="utf-8",
    )
    set_active_config_path(cfg)

    show_call = {
        "function": {
            "name": "show_config",
            "arguments": "{}",
        }
    }
    show_result = await execute_tool_call(show_call)
    assert str(cfg) in show_result
    assert "gpt-default" in show_result

    set_call = {
        "function": {
            "name": "set_config_value",
            "arguments": '{"path": "provider.model", "value": "gpt-new"}',
        }
    }
    set_result = await execute_tool_call(set_call)
    assert "Updated provider.model" in set_result

    data = tomllib.loads(cfg.read_text(encoding="utf-8"))
    assert data["provider"]["model"] == "gpt-new"
    assert data["provider"]["model_params"]["temperature"] == 0.1
