from __future__ import annotations

from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).resolve().parent.parent


def is_reset_command(text: str | None) -> bool:
    """Return True when the input requests a reset (/reset or reset)."""
    if not text:
        return False
    normalized = text.strip().lower()
    return normalized in ("reset", "/reset")


def _load_plugin_content(relative_path: Path, fallback: str) -> str:
    try:
        return relative_path.read_text(encoding="utf-8")
    except OSError:
        return fallback


def _ensure_plugin(config_path: Path, filename: str, content: str) -> Tuple[Path, bool]:
    """
    Ensure the given plugin file exists next to the active config.

    Returns (plugin_path, changed_flag).
    """
    plugin_path = config_path.expanduser().resolve().parent / filename
    plugin_path.parent.mkdir(parents=True, exist_ok=True)

    existing = None
    try:
        existing = plugin_path.read_text(encoding="utf-8")
    except OSError:
        existing = None

    if existing != content:
        plugin_path.write_text(content, encoding="utf-8")
        return plugin_path, True

    return plugin_path, False


_ZSH_PLUGIN_FALLBACK = """# Minimal zsh integration for cli-agent

if [[ -n "${CLI_AGENT_PLUGIN_LOADED:-}" ]] && whence -w _cli_agent_accept_line >/dev/null 2>&1; then
  # Ensure widgets stay bound even if re-sourced.
  zle -N accept-line _cli_agent_accept_line
  zle -N up-line-or-history _cli_agent_history_up
  zle -N down-line-or-history _cli_agent_history_down
  return
fi
CLI_AGENT_PLUGIN_LOADED=1

: "${CLI_AGENT_PREFIX:=@}"
: "${CLI_AGENT_SESSION:=default}"
: "${CLI_AGENT_HISTORY_DIR:=${HOME}/.local/share/cli-agent}"

_cli_agent_history_file="${CLI_AGENT_HISTORY_DIR}/${CLI_AGENT_SESSION}/nl_history.txt"
typeset -g -a _cli_agent_nl_history
typeset -g _cli_agent_nl_index=1

_cli_agent_refresh_history() {
  if [[ -f "${_cli_agent_history_file}" ]]; then
    _cli_agent_nl_history=("${(f)$(<${_cli_agent_history_file})}")
  else
    _cli_agent_nl_history=()
  fi
  _cli_agent_nl_index=$((${#_cli_agent_nl_history[@]} + 1))
}

_cli_agent_refresh_history

_cli_agent_run_payload() {
  local payload="$1"
  local output
  output=$(cli-agent --session "${CLI_AGENT_SESSION}" "${payload}")
  while IFS= read -r line; do
    if [[ "$line" == ADD\\ * ]]; then
      eval "${line#ADD }"
    fi
  done <<< "${output}"
  _cli_agent_refresh_history
}

_cli_agent_accept_line() {
  if [[ "$BUFFER" == "${CLI_AGENT_PREFIX}"* ]]; then
    local payload="${BUFFER#${CLI_AGENT_PREFIX}}"
    # Move output to the next line instead of reprinting the request.
    print
    BUFFER=""
    zle redisplay
    _cli_agent_run_payload "${payload}"
    zle reset-prompt
  else
    if whence -w cli-agent-orig-accept-line >/dev/null 2>&1; then
      zle cli-agent-orig-accept-line
    else
      zle .accept-line
    fi
  fi
}

_cli_agent_history_up() {
  if [[ "$BUFFER" == "${CLI_AGENT_PREFIX}"* ]]; then
    if (( _cli_agent_nl_index > 1 )); then
      (( _cli_agent_nl_index-- ))
      BUFFER="${CLI_AGENT_PREFIX}${_cli_agent_nl_history[_cli_agent_nl_index]}"
      CURSOR=${#BUFFER}
      zle reset-prompt
    else
      zle -M "start of cli-agent history"
    fi
  else
    if whence -w cli-agent-orig-up-line-or-history >/dev/null 2>&1; then
      zle cli-agent-orig-up-line-or-history
    else
      zle .up-line-or-history
    fi
  fi
}

_cli_agent_history_down() {
  if [[ "$BUFFER" == "${CLI_AGENT_PREFIX}"* ]]; then
    if (( _cli_agent_nl_index < ${#_cli_agent_nl_history[@]} )); then
      (( _cli_agent_nl_index++ ))
      BUFFER="${CLI_AGENT_PREFIX}${_cli_agent_nl_history[_cli_agent_nl_index]}"
    else
      _cli_agent_nl_index=$((${#_cli_agent_nl_history[@]} + 1))
      BUFFER="${CLI_AGENT_PREFIX}"
    fi
    CURSOR=${#BUFFER}
    zle reset-prompt
  else
    if whence -w cli-agent-orig-down-line-or-history >/dev/null 2>&1; then
      zle cli-agent-orig-down-line-or-history
    else
      zle .down-line-or-history
    fi
  fi
}

# Preserve original widgets (only if not already captured)
if ! whence -w cli-agent-orig-accept-line >/dev/null 2>&1; then
  if zle -A accept-line cli-agent-orig-accept-line 2>/dev/null; then
    :
  else
    zle -A .accept-line cli-agent-orig-accept-line
  fi
fi
if ! whence -w cli-agent-orig-up-line-or-history >/dev/null 2>&1; then
  if zle -A up-line-or-history cli-agent-orig-up-line-or-history 2>/dev/null; then
    :
  else
    zle -A .up-line-or-history cli-agent-orig-up-line-or-history
  fi
fi
if ! whence -w cli-agent-orig-down-line-or-history >/dev/null 2>&1; then
  if zle -A down-line-or-history cli-agent-orig-down-line-or-history 2>/dev/null; then
    :
  else
    zle -A .down-line-or-history cli-agent-orig-down-line-or-history
  fi
fi

# Override with cli-agent aware widgets
zle -N accept-line _cli_agent_accept_line
zle -N up-line-or-history _cli_agent_history_up
zle -N down-line-or-history _cli_agent_history_down
"""

_BASH_PLUGIN_FALLBACK = """# Minimal bash integration for cli-agent

[[ -n "${BASH_VERSION:-}" ]] || return
[[ -n "${CLI_AGENT_PLUGIN_LOADED:-}" ]] && return

: "${CLI_AGENT_PREFIX:=@}"
: "${CLI_AGENT_SESSION:=default}"
: "${CLI_AGENT_HISTORY_DIR:=${HOME}/.local/share/cli-agent}"

_cli_agent_history_file="${CLI_AGENT_HISTORY_DIR}/${CLI_AGENT_SESSION}/nl_history.txt"
_cli_agent_nl_history=()
_cli_agent_nl_index=0
_cli_agent_shell_hist_offset=0

_cli_agent_prompt_reset() {
  _cli_agent_shell_hist_offset=0
  _cli_agent_nl_index=${#_cli_agent_nl_history[@]}
}

if [[ "$(declare -p PROMPT_COMMAND 2>/dev/null)" == "declare -a"* ]]; then
  PROMPT_COMMAND=(_cli_agent_prompt_reset "${PROMPT_COMMAND[@]}")
else
  PROMPT_COMMAND="_cli_agent_prompt_reset${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
fi

_cli_agent_refresh_history() {
  if [[ -f "${_cli_agent_history_file}" ]]; then
    mapfile -t _cli_agent_nl_history < "${_cli_agent_history_file}"
  else
    _cli_agent_nl_history=()
  fi
  _cli_agent_nl_index=${#_cli_agent_nl_history[@]}
}

_cli_agent_refresh_history

_cli_agent_run_payload() {
  local payload="$1"
  local output
  output=$(cli-agent --session "${CLI_AGENT_SESSION}" "${payload}")
  while IFS= read -r line; do
    if [[ "$line" == ADD\\ * ]]; then
      eval "${line#ADD }"
    fi
  done <<< "${output}"
  _cli_agent_refresh_history
}

_cli_agent_history_up() {
  local prefix="${CLI_AGENT_PREFIX}"
  if [[ "$READLINE_LINE" == "${prefix}"* ]]; then
    _cli_agent_shell_hist_offset=0
    if (( _cli_agent_nl_index > 0 )); then
      ((_cli_agent_nl_index--))
      READLINE_LINE="${prefix}${_cli_agent_nl_history[_cli_agent_nl_index]}"
      READLINE_POINT=${#READLINE_LINE}
    fi
    return
  fi

  local max_offset=$((HISTCMD - 1))
  if (( _cli_agent_shell_hist_offset < max_offset )); then
    ((_cli_agent_shell_hist_offset++))
    local entry
    local target=$((HISTCMD - _cli_agent_shell_hist_offset))
    entry=$(builtin history -p "!${target}" 2>/dev/null)
    entry=${entry%$'\\n'}
    if [[ -n "${entry}" ]]; then
      READLINE_LINE="${entry}"
      READLINE_POINT=${#READLINE_LINE}
    fi
  fi
}

_cli_agent_history_down() {
  local prefix="${CLI_AGENT_PREFIX}"
  if [[ "$READLINE_LINE" == "${prefix}"* ]]; then
    _cli_agent_shell_hist_offset=0
    local total=${#_cli_agent_nl_history[@]}
    if (( _cli_agent_nl_index < total )); then
      ((_cli_agent_nl_index++))
      if (( _cli_agent_nl_index == total )); then
        READLINE_LINE="${prefix}"
      else
        READLINE_LINE="${prefix}${_cli_agent_nl_history[_cli_agent_nl_index]}"
      fi
      READLINE_POINT=${#READLINE_LINE}
    fi
    return
  fi

  if (( _cli_agent_shell_hist_offset > 1 )); then
    ((_cli_agent_shell_hist_offset--))
    local entry
    local target=$((HISTCMD - _cli_agent_shell_hist_offset))
    entry=$(builtin history -p "!${target}" 2>/dev/null)
    entry=${entry%$'\\n'}
    READLINE_LINE="${entry}"
    READLINE_POINT=${#READLINE_LINE}
  elif (( _cli_agent_shell_hist_offset == 1 )); then
    _cli_agent_shell_hist_offset=0
    READLINE_LINE=""
    READLINE_POINT=0
  fi
}

bind -x '"\\e[A":_cli_agent_history_up'
bind -x '"\\e[B":_cli_agent_history_down'

if declare -f command_not_found_handle >/dev/null 2>&1; then
  eval "$(declare -f command_not_found_handle | sed '1s/command_not_found_handle/_cli_agent_prev_command_not_found_handle/')"
fi

command_not_found_handle() {
  local cmd="$1"
  shift || true

  if [[ "$cmd" == "${CLI_AGENT_PREFIX}"* ]]; then
    local payload="${cmd#${CLI_AGENT_PREFIX}}"
    if (($#)); then
      payload+=" $*"
    fi
    printf '\\n'
    _cli_agent_run_payload "${payload}"
    _cli_agent_shell_hist_offset=0
    return 0
  fi

  if declare -f _cli_agent_prev_command_not_found_handle >/dev/null 2>&1; then
    _cli_agent_prev_command_not_found_handle "$cmd" "$@"
    return $?
  fi

  printf 'bash: %s: command not found\\n' "$cmd" >&2
  return 127
}

CLI_AGENT_PLUGIN_LOADED=1
"""

DEFAULT_ZSH_PLUGIN_CONTENT = _load_plugin_content(
    ROOT / "zsh" / "plugin.zsh", _ZSH_PLUGIN_FALLBACK
)
DEFAULT_BASH_PLUGIN_CONTENT = _load_plugin_content(
    ROOT / "bash" / "plugin.bash", _BASH_PLUGIN_FALLBACK
)


def ensure_zsh_plugin(config_path: Path) -> Tuple[Path, bool]:
    """
    Ensure the zsh plugin is written next to the active config.

    Returns (plugin_path, changed_flag).
    """
    return _ensure_plugin(config_path, "plugin.zsh", DEFAULT_ZSH_PLUGIN_CONTENT)


def ensure_bash_plugin(config_path: Path) -> Tuple[Path, bool]:
    """
    Ensure the bash plugin is written next to the active config.

    Returns (plugin_path, changed_flag).
    """
    return _ensure_plugin(config_path, "plugin.bash", DEFAULT_BASH_PLUGIN_CONTENT)
