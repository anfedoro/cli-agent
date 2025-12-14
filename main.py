from __future__ import annotations

import argparse
import asyncio
import sys
import os
from pathlib import Path
import signal

from agent.config import (
    AppConfig,
    ConfigError,
    AgentConfig,
    find_config_path,
    initialize_default_config,
    load_app_config,
)
from agent.history import HistoryStore
from agent.loop import run_agent
from agent.ui import build_console
from agent.utils import ensure_zsh_plugin, is_reset_command

APP_VERSION = "0.4.2"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CLI agent backend", add_help=True)
    parser.add_argument("request", nargs="?", help='User request text, e.g. "Summarize README"')
    parser.add_argument(
        "--input",
        help="Request text (alias for positional request; useful for wrapper compatibility)",
    )
    parser.add_argument(
        "--mode",
        choices=["agent"],
        default="agent",
        help="Compatibility flag for wrappers; only 'agent' mode is supported",
    )
    parser.add_argument("--reset", action="store_true", help="Reset stored history for the session")
    parser.add_argument("--config", help="Path to config TOML file")
    parser.add_argument("--session", help="Session name (overrides config)")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    args = parser.parse_args(argv)
    if args.request and args.input:
        parser.error("Provide request as a positional argument or via --input, not both.")
    return args


def load_config(args: argparse.Namespace) -> AppConfig:
    cli_path = Path(args.config).expanduser() if args.config else None
    if cli_path and not cli_path.is_file():
        raise ConfigError(f"Config file not found: {cli_path}")

    auto_path = cli_path or find_config_path()
    if not auto_path:
        auto_path = initialize_default_config(os.getenv("CLI_AGENT_CONFIG"))
        print(f"Initialized default config at {auto_path}", file=sys.stderr)
    config = load_app_config(auto_path)

    if args.session:
        config.agent = AgentConfig(
            max_steps=config.agent.max_steps,
            timeout_sec=config.agent.timeout_sec,
            max_tool_calls_per_step=config.agent.max_tool_calls_per_step,
            history_dir=config.agent.history_dir,
            session=args.session,
        )

    return config


def handle_reset(history: HistoryStore) -> int:
    history.reset()
    print("✅ reset", file=sys.stderr)
    return 0


def _install_status_signals(config: AppConfig) -> None:
    def _status_handler(signum, frame) -> None:  # type: ignore[override]
        print(
            f"[cli-agent] status: model={config.provider.model}, session={config.agent.session}",
            file=sys.stderr,
        )

    for sig_name in ("SIGUSR1", "SIGINFO"):
        sig = getattr(signal, sig_name, None)
        if sig:
            try:
                signal.signal(sig, _status_handler)
            except (ValueError, OSError):
                pass


def main() -> int:
    if len(sys.argv) == 1:
        return 0

    args = parse_args(sys.argv[1:])

    try:
        config = load_config(args)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    plugin_path, plugin_changed = ensure_zsh_plugin(config.path or Path("~/.config/cli-agent/config.toml"))
    if plugin_changed:
        print(
            f"Installed zsh plugin at {plugin_path}. Add 'source {plugin_path}' to your ~/.zshrc to enable the @ prefix.",
            file=sys.stderr,
        )

    if args.version:
        print(f"cli-agent {APP_VERSION}")
        return 0

    _install_status_signals(config)

    history = HistoryStore(config.agent.history_dir, args.session or config.agent.session)

    request_text = args.request or args.input
    if args.reset or is_reset_command(request_text):
        return handle_reset(history)

    if not request_text:
        return 0

    console = build_console(config.ui.rich)

    try:
        result = asyncio.run(run_agent(request_text, config, history, console))
        return result.exit_code
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
