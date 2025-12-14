# Minimal bash integration for cli-agent

[[ -n "${BASH_VERSION:-}" ]] || return

: "${CLI_AGENT_PREFIX:=@}"
: "${CLI_AGENT_SESSION:=default}"
: "${CLI_AGENT_HISTORY_DIR:=${HOME}/.local/share/cli-agent}"

_cli_agent_history_file="${CLI_AGENT_HISTORY_DIR}/${CLI_AGENT_SESSION}/nl_history.txt"
_cli_agent_nl_history=()
_cli_agent_nl_index=0
_cli_agent_shell_hist_offset=0

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
    if [[ "$line" == ADD\ * ]]; then
      eval "${line#ADD }"
    fi
  done <<< "${output}"
  _cli_agent_refresh_history
}

_cli_agent_accept_line() {
  local prefix="${CLI_AGENT_PREFIX}"
  if [[ "$READLINE_LINE" == "${prefix}"* ]]; then
    local payload="${READLINE_LINE#${prefix}}"
    printf '\n'
    _cli_agent_run_payload "${payload}"
    READLINE_LINE=""
    READLINE_POINT=0
    _cli_agent_shell_hist_offset=0
  else
    READLINE_DONE=1
    READLINE_POINT=${#READLINE_LINE}
    _cli_agent_shell_hist_offset=0
  fi
}

_cli_agent_history_up() {
  local prefix="${CLI_AGENT_PREFIX}"
  if [[ "$READLINE_LINE" == "${prefix}"* ]]; then
    if (( _cli_agent_nl_index > 0 )); then
      ((_cli_agent_nl_index--))
      READLINE_LINE="${prefix}${_cli_agent_nl_history[_cli_agent_nl_index]}"
      READLINE_POINT=${#READLINE_LINE}
    fi
    return
  fi

  local limit=${HISTCMD:-0}
  if (( _cli_agent_shell_hist_offset < limit )); then
    ((_cli_agent_shell_hist_offset++))
    local entry
    entry=$(fc -ln -${_cli_agent_shell_hist_offset} -${_cli_agent_shell_hist_offset} 2>/dev/null)
    if [[ -n "${entry}" ]]; then
      READLINE_LINE="${entry}"
      READLINE_POINT=${#READLINE_LINE}
    fi
  fi
}

_cli_agent_history_down() {
  local prefix="${CLI_AGENT_PREFIX}"
  if [[ "$READLINE_LINE" == "${prefix}"* ]]; then
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
    entry=$(fc -ln -${_cli_agent_shell_hist_offset} -${_cli_agent_shell_hist_offset} 2>/dev/null)
    READLINE_LINE="${entry}"
    READLINE_POINT=${#READLINE_LINE}
  elif (( _cli_agent_shell_hist_offset == 1 )); then
    _cli_agent_shell_hist_offset=0
    READLINE_LINE=""
    READLINE_POINT=0
  fi
}

bind -x '"\C-m":_cli_agent_accept_line'
bind -x '"\C-j":_cli_agent_accept_line'
bind -x '"\e[A":_cli_agent_history_up'
bind -x '"\e[B":_cli_agent_history_down'

CLI_AGENT_PLUGIN_LOADED=1
