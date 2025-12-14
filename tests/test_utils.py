from pathlib import Path

from agent.utils import (
    DEFAULT_BASH_PLUGIN_CONTENT,
    DEFAULT_ZSH_PLUGIN_CONTENT,
    ensure_bash_plugin,
    ensure_zsh_plugin,
    is_reset_command,
)


def test_is_reset_command_variants():
    assert is_reset_command("reset")
    assert is_reset_command("/reset")
    assert is_reset_command("  /reset  ")
    assert not is_reset_command("reset now")
    assert not is_reset_command(None)


def test_ensure_zsh_plugin_writes_content(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("", encoding="utf-8")

    plugin_path, changed = ensure_zsh_plugin(cfg)
    assert changed is True
    assert plugin_path.exists()
    assert plugin_path.read_text(encoding="utf-8") == DEFAULT_ZSH_PLUGIN_CONTENT

    # second call is idempotent
    plugin_path, changed_again = ensure_zsh_plugin(cfg)
    assert changed_again is False


def test_ensure_bash_plugin_writes_content(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("", encoding="utf-8")

    plugin_path, changed = ensure_bash_plugin(cfg)
    assert changed is True
    assert plugin_path.exists()
    assert plugin_path.read_text(encoding="utf-8") == DEFAULT_BASH_PLUGIN_CONTENT

    plugin_path, changed_again = ensure_bash_plugin(cfg)
    assert changed_again is False
