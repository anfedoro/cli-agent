# Minimal zsh integration for cli-agent

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
    if [[ "$line" == ADD\ * ]]; then
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
    zle redisplay
  else
    zle cli-agent-orig-accept-line
  fi
}

_cli_agent_history_up() {
  if [[ "$BUFFER" == "${CLI_AGENT_PREFIX}"* ]]; then
    if (( _cli_agent_nl_index > 1 )); then
      (( _cli_agent_nl_index-- ))
      BUFFER="${CLI_AGENT_PREFIX}${_cli_agent_nl_history[_cli_agent_nl_index]}"
      CURSOR=${#BUFFER}
      zle redisplay
    else
      zle -M "start of cli-agent history"
    fi
  else
    zle cli-agent-orig-up-line-or-history
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
    zle redisplay
  else
    zle cli-agent-orig-down-line-or-history
  fi
}

# Preserve original widgets (only if not already captured)
if ! whence -w cli-agent-orig-accept-line >/dev/null 2>&1; then
  zle -A accept-line cli-agent-orig-accept-line
fi
if ! whence -w cli-agent-orig-up-line-or-history >/dev/null 2>&1; then
  zle -A up-line-or-history cli-agent-orig-up-line-or-history
fi
if ! whence -w cli-agent-orig-down-line-or-history >/dev/null 2>&1; then
  zle -A down-line-or-history cli-agent-orig-down-line-or-history
fi

# Override with cli-agent aware widgets
zle -N accept-line _cli_agent_accept_line
zle -N up-line-or-history _cli_agent_history_up
zle -N down-line-or-history _cli_agent_history_down
