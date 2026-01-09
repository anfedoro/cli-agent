import json
import sys
import tomllib

import pytest

from agent.tools import (
    execute_tool_call,
    get_active_workdir,
    set_active_config_path,
    set_active_workdir,
)


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


@pytest.mark.asyncio
async def test_run_cmd_tracks_cwd(tmp_path):
    set_active_workdir(None)
    set_active_workdir(tmp_path)

    cmd = f'"{sys.executable}" -c "import os; print(os.getcwd())"'
    run_call = {
        "function": {
            "name": "run_cmd",
            "arguments": json.dumps({"cmd": cmd}),
        }
    }
    run_result = await execute_tool_call(run_call)
    payload = json.loads(run_result)
    assert payload["stdout"].strip() == str(tmp_path.resolve())

    child = tmp_path / "child"
    child.mkdir()
    cd_call = {
        "function": {
            "name": "run_cmd",
            "arguments": json.dumps({"cmd": "cd child"}),
        }
    }
    await execute_tool_call(cd_call)
    assert get_active_workdir() == child.resolve()

    set_active_workdir(None)
