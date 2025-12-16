import sys
from types import SimpleNamespace

import pytest

import main
from agent.config import AgentConfig, UIConfig
from main import parse_args


def test_parse_args_accepts_mode_and_input():
    args = parse_args(["--mode", "agent", "--input", "hello"])
    assert args.input == "hello"
    assert args.request is None


def test_parse_args_errors_on_conflicting_request_and_input():
    with pytest.raises(SystemExit):
        parse_args(["--mode", "agent", "hello", "--input", "world"])


def test_main_handles_slash_reset(monkeypatch, tmp_path):
    calls = []

    def fake_handle_reset(history):
        calls.append("reset")
        return 0

    config = SimpleNamespace(
        agent=AgentConfig(history_dir=tmp_path, session="demo"),
        ui=UIConfig(rich=False),
        prompt=None,
        provider=None,
        tools={},
        path=tmp_path / "config.toml",
    )

    monkeypatch.setattr(main, "load_config", lambda args: config)
    monkeypatch.setattr(main, "handle_reset", fake_handle_reset)
    monkeypatch.setattr(main, "HistoryStore", lambda *a, **k: SimpleNamespace(reset=lambda: None))
    monkeypatch.setattr(sys, "argv", ["cli-agent", "/reset"])

    exit_code = main.main()

    assert exit_code == 0
    assert calls == ["reset"]


def test_main_handles_reset_session(monkeypatch, tmp_path):
    calls = []

    def fake_handle_reset(history):
        calls.append("reset")
        return 0

    config = SimpleNamespace(
        agent=AgentConfig(history_dir=tmp_path, session="demo"),
        ui=UIConfig(rich=False),
        prompt=None,
        provider=None,
        tools={},
        path=tmp_path / "config.toml",
    )

    monkeypatch.setattr(main, "load_config", lambda args: config)
    monkeypatch.setattr(main, "handle_reset", fake_handle_reset)
    monkeypatch.setattr(main, "HistoryStore", lambda *a, **k: SimpleNamespace(reset=lambda: None))
    monkeypatch.setattr(sys, "argv", ["cli-agent", "reset_session"])

    exit_code = main.main()

    assert exit_code == 0
    assert calls == ["reset"]
