import os
from pathlib import Path

import pytest

import agent.config as config_module
from agent.config import AppConfig, AgentConfig, ConfigError, ProviderConfig, UIConfig, find_config_path, load_app_config


def test_find_config_prefers_cli_path(tmp_path, monkeypatch):
    cli_config = tmp_path / "cli.toml"
    env_config = tmp_path / "env.toml"
    cli_config.write_text("[provider]\nname = 'openai'\n", encoding="utf-8")
    env_config.write_text("[provider]\nname = 'openai'\n", encoding="utf-8")

    monkeypatch.setenv("CLI_AGENT_CONFIG", str(env_config))
    found = find_config_path(str(cli_config))
    assert found == cli_config.resolve()


def test_load_app_config_defaults_when_missing():
    config = load_app_config(None)
    assert isinstance(config, AppConfig)
    assert config.provider.name == "openai"
    assert config.provider.model_params == {}
    assert config.agent.max_steps == 20
    assert config.agent.follow_cwd is True
    assert config.ui.rich is True
    assert config.prompt.custom_prompt == ""
    assert config.prompt.custom_prompt_mode == "developer"
    assert config.prompt.system_prompt


def test_load_app_config_reads_values(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[provider]
name = "openai"
api_key_env = "TEST_KEY"
model = "gpt-4o-mini"
[provider.model_params]
temperature = 0.3
reasoning_effort = "medium"

[agent]
max_steps = 3
timeout_sec = 5
history_dir = "{history}"
session = "demo"
follow_cwd = false

[prompt]
system_prompt = "Be nice"
custom_prompt = "Add logs"
custom_prompt_mode = "system"

[ui]
rich = false
show_tool_args = false
        """.format(history=tmp_path / "hist"),
        encoding="utf-8",
    )

    config = load_app_config(config_path)
    assert config.provider.api_key_env == "TEST_KEY"
    assert config.provider.model == "gpt-4o-mini"
    assert config.provider.model_params == {"temperature": 0.3, "reasoning_effort": "medium"}
    assert config.agent.max_steps == 3
    assert config.agent.timeout_sec == 5
    assert config.agent.history_dir.name == "hist"
    assert config.agent.session == "demo"
    assert config.agent.follow_cwd is False
    assert config.ui.rich is False
    assert config.ui.show_tool_args is False
    assert config.prompt.system_prompt == "Be nice"
    assert config.prompt.custom_prompt == "Add logs"
    assert config.prompt.custom_prompt_mode == "system"


def test_load_app_config_accepts_flat_provider_keys(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
name = "alt"
base_url = "http://example.com"
api_key_env = "OTHER"
model = "gpt-test"
model_params = {temperature = 0.2}
        """,
        encoding="utf-8",
    )

    config = load_app_config(config_path)
    assert config.provider.name == "alt"
    assert config.provider.base_url == "http://example.com"
    assert config.provider.api_key_env == "OTHER"
    assert config.provider.model == "gpt-test"
    assert config.provider.model_params == {"temperature": 0.2}


def test_load_app_config_rejects_invalid_custom_prompt_mode(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[prompt]
custom_prompt_mode = "unknown"
        """,
        encoding="utf-8",
    )

    with pytest.raises(ConfigError):
        load_app_config(config_path)


def test_initialize_default_config_creates_file(tmp_path, monkeypatch):
    target = tmp_path / "cli-agent" / "config.toml"
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG_PATHS", [str(target)])

    created = config_module.initialize_default_config()

    assert created == target.resolve()
    assert target.is_file()
    loaded = load_app_config(created)
    assert loaded.provider.model == "gpt-4.1-mini"
    assert loaded.agent.history_dir.name == "cli-agent"
    assert loaded.prompt.system_prompt == config_module.DEFAULT_SYSTEM_PROMPT


def test_initialize_default_config_prefers_env_path(tmp_path, monkeypatch):
    env_target = tmp_path / "env" / "config.toml"
    fallback = tmp_path / "fallback" / "config.toml"
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG_PATHS", [str(fallback)])

    created = config_module.initialize_default_config(str(env_target))

    assert created == env_target.resolve()
    assert env_target.is_file()
    assert not fallback.exists()


def test_empty_system_prompt_uses_default(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        """
[prompt]
system_prompt = ""
        """,
        encoding="utf-8",
    )

    loaded = load_app_config(cfg)
    assert loaded.prompt.system_prompt == config_module.DEFAULT_SYSTEM_PROMPT
