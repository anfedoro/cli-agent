# CLI Agent

Async CLI backend for LLM-powered automation. The agent runs as a single command, loads configuration from TOML, executes tool/function calls in a loop, and emits shell directives via the `ADD <cmd>` protocol on stdout while showing progress on stderr.

## Quickstart
1. Install deps: `uv sync --extra dev` (or `pip install -e .[dev]`).
2. Provide an API key: `export OPENAI_API_KEY=...` (configurable `api_key_env`).
3. Install the CLI: `uv tool install .` (installs `cli-agent` on PATH).
4. Run once (e.g., `cli-agent --version`) to bootstrap config and shell plugins at `~/.config/cli-agent/plugin.{zsh,bash}` (or alongside your chosen `--config`).
5. Source the matching plugin in your shell init (`~/.zshrc` or `~/.bashrc`), open a new shell, and use the `@` prefix (e.g., `@summarize README.md`). Use `@reset_session` to clear chat/nl history locally.

Install globally with `uv tool install .` to make `cli-agent` available on PATH. Running with no arguments prints nothing and exits successfully.

## Configuration (TOML)
Search order: `--config` flag > `CLI_AGENT_CONFIG` env > `~/.config/cli-agent/config.toml` > `./config.toml`.
If nothing is found, cli-agent writes a default config to `CLI_AGENT_CONFIG` (when set) or `~/.config/cli-agent/config.toml`; a template copy is available at `config.example.toml`.
- The system prompt is baked into the binary and not written to configs. Leave `prompt.system_prompt` empty to use it; override only if you accept weaker safety.
- Extra OpenAI parameters (e.g., `temperature`, `max_output_tokens`, `reasoning_effort`) can be set under `[provider.model_params]` and are passed through as-is.

```toml
[provider]
name = "openai"
api_key_env = "OPENAI_API_KEY"
model = "gpt-4.1-mini"
base_url = ""
[provider.model_params]
# temperature = 0.0
# max_output_tokens = 1024
# reasoning_effort = "medium"

[agent]
max_steps = 20
timeout_sec = 90
max_tool_calls_per_step = 10
history_dir = "~/.local/share/cli-agent"
session = "default"

[prompt]
# leave blank to use the built-in secure system prompt (recommended)
system_prompt = ""
custom_prompt = ""
custom_prompt_mode = "developer"  # or "system" to append to the system message

[ui]
rich = true
show_tool_args = true
show_step_summary = true
```

## How It Works
- CLI builds message history from `history_dir/<session>/chat.jsonl` and appends the new request.
- History is stored as lean lines (`role<TAB>content`): user text, tool call summaries (`tool\tname(args)`), and assistant replies; tool outputs are not persisted. Legacy JSON history is compacted on read.
- Async LLM calls (OpenAI client) run under a Rich spinner on stderr.
- Tool calls are executed (`write_file`, `read_file`, `run_cmd`, `ask_user`), recorded in history, and iterated until completion or `max_steps`.
- Final assistant text prints to stderr; lines starting with `ADD ` are emitted on stdout only for shell execution.
- Reset clears `chat.jsonl` and `nl_history.txt` without touching config; use `@reset_session` (or legacy `/reset`) to trigger it locally without an LLM call.
- Prompts: leave `prompt.system_prompt` empty to use the built-in secure prompt. `prompt.custom_prompt` is added as a developer message (or appended to the system message when `prompt.custom_prompt_mode` is `"system"`).
- Legacy keys from older configs (e.g., `default_mode`, `history_length`, `prompt_indicator`, `system_prompt_file/system_prompt_text`) are ignored.

## History & NL Commands
- Chat and tool traces: `history_dir/<session>/chat.jsonl`
- Natural-language shell prefix entries: `history_dir/<session>/nl_history.txt`
- `cli-agent Reset` or `cli-agent --reset` truncates both files atomically.

## Shell Plugins
The CLI writes `plugin.zsh` and `plugin.bash` next to your active config (default `~/.config/cli-agent/`) and prints a reminder when it creates/updates them. Source the one that matches your shell to enable the `@` prefix and nl-history navigation.
- Common: Enter runs `cli-agent "<payload>"`; stdout `ADD ...` lines are executed; stderr shows the Rich UI.
- zsh: `source ~/.config/cli-agent/plugin.zsh`; Up/Down arrows cycle through `nl_history.txt` when the prefix is present.
- bash: `source ~/.config/cli-agent/plugin.bash`; Up/Down arrows walk `nl_history.txt` for prefixed input while regular shell history keeps working otherwise; the plugin hooks `command_not_found_handle` to reroute `@...` commands (existing handlers are preserved). Bash treats `/` in command names as paths, so use `@reset_session` (not `@/reset`) for local reset.

### Built-in @ commands
- `@reset_session` — truncate chat/nl history for the current session.
- `@show_config` — print the active config file.
- `@show_help` — short help on prefix usage.
- `@update config <text>` — send a config change request to the agent (forwarded to the LLM).

## Development
- Tests: `uv run pytest` (smoke tests mock the LLM client; no network needed).
- Coding style: PEP 8, stdout reserved for `ADD` directives, UI on stderr.
- Entry point: `main.py`; core modules live in `agent/config.py`, `agent/history.py`, `agent/llm_client.py`, `agent/tools.py`, `agent/loop.py`, `agent/ui.py`.
