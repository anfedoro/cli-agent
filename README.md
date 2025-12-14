# CLI Agent

Async CLI backend for LLM-powered automation. The agent runs as a single command, loads configuration from TOML, executes tool/function calls in a loop, and emits shell directives via the `ADD <cmd>` protocol on stdout while showing progress on stderr.

## Quickstart
1. Install deps: `uv sync --extra dev` (or `pip install -e .[dev]`).
2. Provide an API key: `export OPENAI_API_KEY=...` (configurable `api_key_env`).
3. Run requests:
   - `cli-agent "Summarize the repo"`
   - `cli-agent --mode agent --input "Summarize the repo"` (compatibility with wrappers using mode/input flags)
   - `cli-agent --version` (check installed version)
   - `cli-agent --reset` (truncate chat and nl history)
   - `cli-agent --config /path/config.toml --session demo "Plan work"`

Install globally with `uv tool install .` to make `cli-agent` available on PATH. Running with no arguments prints nothing and exits successfully.

## Configuration (TOML)
Search order: `--config` flag > `CLI_AGENT_CONFIG` env > `~/.config/cli-agent/config.toml` > `./config.toml`.
If nothing is found, cli-agent writes a default config to `CLI_AGENT_CONFIG` (when set) or `~/.config/cli-agent/config.toml`; a template copy is available at `config.example.toml`.
- A built-in secure system prompt is used unless you explicitly set `prompt.system_prompt` in the config; overriding it is possible but may weaken safety.
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
system_prompt = "You are cli-agent..."
custom_prompt = ""
custom_prompt_mode = "developer"  # or "system" to append to the system message

[ui]
rich = true
show_tool_args = true
show_step_summary = true
```

## How It Works
- CLI builds message history from `history_dir/<session>/chat.jsonl` and appends the new request.
- Async LLM calls (OpenAI client) run under a Rich spinner on stderr.
- Tool calls are executed (`write_file`, `read_file`, `run_cmd`, `ask_user`), recorded in history, and iterated until completion or `max_steps`.
- Final assistant text prints to stderr; lines starting with `ADD ` are emitted on stdout only for shell execution.
- Reset clears `chat.jsonl` and `nl_history.txt` without touching config.
- Prompts: `prompt.system_prompt` sets the base instructions; `prompt.custom_prompt` is added as a developer
  message (or appended to the system message when `prompt.custom_prompt_mode` is `"system"`).
- Legacy keys from older configs (e.g., `default_mode`, `history_length`, `prompt_indicator`, `system_prompt_file/system_prompt_text`) are ignored.

## History & NL Commands
- Chat and tool traces: `history_dir/<session>/chat.jsonl`
- Natural-language shell prefix entries: `history_dir/<session>/nl_history.txt`
- `cli-agent Reset` or `cli-agent --reset` truncates both files atomically.

## zsh Plugin
Source `zsh/plugin.zsh` to enable a prefix trigger (default `@`). With the prefix in the buffer:
- Enter runs `cli-agent "<payload>"`.
- Stdout `ADD ...` lines are executed; stderr shows the Rich UI.
- Up/Down arrows cycle through `nl_history.txt`; without the prefix, shell history behaves normally.

## Development
- Tests: `uv run pytest` (smoke tests mock the LLM client; no network needed).
- Coding style: PEP 8, stdout reserved for `ADD` directives, UI on stderr.
- Entry point: `main.py`; core modules live in `agent/config.py`, `agent/history.py`, `agent/llm_client.py`, `agent/tools.py`, `agent/loop.py`, `agent/ui.py`.
