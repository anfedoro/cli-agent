from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, Optional


class ConfigError(Exception):
    """Raised when configuration cannot be loaded or parsed."""


@dataclass
class ProviderConfig:
    name: str = "openai"
    base_url: Optional[str] = None
    api_key_env: str = "OPENAI_API_KEY"
    model: str = "gpt-4.1-mini"
    model_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentConfig:
    max_steps: int = 20
    timeout_sec: int = 90
    max_tool_calls_per_step: int = 10
    history_dir: Path = Path("~/.local/share/cli-agent")
    session: str = "default"
    follow_cwd: bool = True


DEFAULT_SYSTEM_PROMPT = dedent(
    """
    # Terminal Agent — Cross-Platform

    Role: You are a terminal agent with cross-platform CLI access (Windows PowerShell/CMD; Linux/Unix shells).

    SECURITY
    - NEVER install software without explicit user permission.
    - Check tool availability first: run with --version or --help.
    - Prefer PowerShell on Windows; POSIX shells on Unix.
    - If a required tool is missing: say which tool and ask:
      "To proceed, I need to install [tool]. May I do so?"

    EXECUTION STRATEGY
    1. Identify necessary commands for the request.
    2. Verify tools (see SECURITY).
    3. If install needed — request permission; only proceed after confirmation.
    4. Execute commands once tools are confirmed.
    5. Analyze results:
       - If success -> provide result without extra calls.
       - If fail/unclear -> adjust and retry (max {MAX_AGENT_ITERATIONS}).
       - If still no solution -> explain the issue and offer alternatives.
    6. Run multiple commands sequentially if required, but be strategic.

    COMMAND ERROR HANDLING
    - For "command not found": propose correct spelling, alternatives, or installation.
    - For permission/syntax errors: give specific fixes.
    - Distinguish typos vs. natural-language questions.
    - If user shares a failed command, focus on that failure.

    SHELL MODE BEHAVIOR
    - Be concise and task-focused; no fluff.
    - Present successful command outputs cleanly.

    COMPLETION RULES
    - ALWAYS show command outputs verbatim in fenced code blocks, unmodified.
    - Show ALL output lines; do not summarize or truncate. If output is very long (>100 lines), still show it all, then suggest filters.
    - After the complete output, you may add brief commentary.
    - After 2-3 unsuccessful attempts, explain clearly and propose alternatives.
    - Respond concisely in the user's prompt language.
    - Preserve original output formatting.
    - Visually separate raw output (code, outcome, explanations, recommendations etc.) via clear labels.
    """
).strip()


@dataclass
class PromptConfig:
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    custom_prompt: str = ""
    custom_prompt_mode: str = "developer"  # developer or system


@dataclass
class UIConfig:
    rich: bool = True
    show_tool_args: bool = True
    show_step_summary: bool = True


@dataclass
class AppConfig:
    provider: ProviderConfig
    agent: AgentConfig
    ui: UIConfig
    prompt: PromptConfig = field(default_factory=PromptConfig)
    tools: Dict[str, Any] = field(default_factory=dict)
    path: Optional[Path] = None


DEFAULT_CONFIG_PATHS = [
    "~/.config/cli-agent/config.toml",
    "./config.toml",
]


def _build_default_config_template() -> str:
    return f"""# Default cli-agent configuration
[provider]
name = "openai"
api_key_env = "OPENAI_API_KEY"
model = "gpt-4.1-mini"
base_url = ""
[provider.model_params]
# temperature = 0.0
# top_p = 1.0
# max_output_tokens = 1024
# reasoning_effort = "medium"  # e.g., for reasoning-capable models

[agent]
max_steps = 20
timeout_sec = 90
max_tool_calls_per_step = 10
history_dir = "~/.local/share/cli-agent"
session = "default"
follow_cwd = true

[prompt]
# Leave blank to use the built-in secure system prompt. Override at your own risk.
system_prompt = ""
custom_prompt = ""
custom_prompt_mode = "developer"

[ui]
rich = true
show_tool_args = true
show_step_summary = true
"""


DEFAULT_CONFIG_TEMPLATE = _build_default_config_template()


def _expand_path(path_value: str | Path) -> Path:
    return Path(path_value).expanduser().resolve()


def find_config_path(cli_argument: Optional[str] = None) -> Optional[Path]:
    """Return the first existing config path using the required priority."""
    candidates = []
    if cli_argument:
        candidates.append(Path(cli_argument))
    env_path = os.getenv("CLI_AGENT_CONFIG")
    if env_path:
        candidates.append(Path(env_path))
    candidates.extend(Path(p) for p in DEFAULT_CONFIG_PATHS)

    for candidate in candidates:
        expanded = _expand_path(candidate)
        if expanded.is_file():
            return expanded
    return None


def initialize_default_config(env_config_path: Optional[str] = None) -> Path:
    """
    Write a default config to the first writable location and return its path.

    The search order respects CLI_AGENT_CONFIG when provided, then DEFAULT_CONFIG_PATHS.
    """
    candidates: list[Path] = []
    if env_config_path:
        candidates.append(Path(env_config_path))
    candidates.extend(Path(p) for p in DEFAULT_CONFIG_PATHS)

    errors: list[str] = []
    for candidate in candidates:
        target = _expand_path(candidate)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
            return target
        except OSError as exc:
            errors.append(f"{target}: {exc}")

    detail = "; ".join(errors) if errors else "no candidate paths"
    raise ConfigError(f"Unable to create default config ({detail}).")


def _load_raw_config(path: Path) -> Dict[str, Any]:
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except FileNotFoundError as exc:
        raise ConfigError(f"Config file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in config: {path}") from exc


def load_app_config(path: Optional[Path]) -> AppConfig:
    raw_config = _load_raw_config(path) if path else {}

    provider_data = raw_config.get("provider")
    if not provider_data:
        # Legacy configs might place provider keys at the root.
        fallback_keys = ("name", "base_url", "api_key_env", "model", "model_params")
        provider_data = {k: raw_config.get(k) for k in fallback_keys if k in raw_config}
    if provider_data is None:
        provider_data = {}
    provider = ProviderConfig(
        name=provider_data.get("name", "openai"),
        base_url=provider_data.get("base_url"),
        api_key_env=provider_data.get("api_key_env", "OPENAI_API_KEY"),
        model=provider_data.get("model", "gpt-4.1-mini"),
        model_params=provider_data.get("model_params", {}) or {},
    )

    agent_data = raw_config.get("agent", {})
    history_dir = agent_data.get("history_dir", "~/.local/share/cli-agent")
    agent = AgentConfig(
        max_steps=int(agent_data.get("max_steps", 20)),
        timeout_sec=int(agent_data.get("timeout_sec", 90)),
        max_tool_calls_per_step=int(agent_data.get("max_tool_calls_per_step", 10)),
        history_dir=_expand_path(history_dir),
        session=str(agent_data.get("session", "default")),
        follow_cwd=bool(agent_data.get("follow_cwd", True)),
    )

    prompt_data = raw_config.get("prompt", {}) or {}
    custom_mode = prompt_data.get("custom_prompt_mode", "developer")
    if custom_mode not in ("developer", "system"):
        raise ConfigError("prompt.custom_prompt_mode must be 'developer' or 'system'")
    sys_prompt_raw = prompt_data.get("system_prompt")
    system_prompt = DEFAULT_SYSTEM_PROMPT if sys_prompt_raw is None or str(sys_prompt_raw).strip() == "" else sys_prompt_raw
    prompt = PromptConfig(
        system_prompt=system_prompt,
        custom_prompt=prompt_data.get("custom_prompt", ""),
        custom_prompt_mode=custom_mode,
    )

    ui_data = raw_config.get("ui", {})
    ui = UIConfig(
        rich=bool(ui_data.get("rich", True)),
        show_tool_args=bool(ui_data.get("show_tool_args", True)),
        show_step_summary=bool(ui_data.get("show_step_summary", True)),
    )

    tools_data = raw_config.get("tools", {}) or {}

    return AppConfig(provider=provider, agent=agent, prompt=prompt, ui=ui, tools=tools_data, path=path)
