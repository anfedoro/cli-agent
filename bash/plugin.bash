# Minimal bash integration for cli-agent

[[ -n "${BASH_VERSION:-}" ]] || return

: "${CLI_AGENT_PREFIX:=@}"
: "${CLI_AGENT_SESSION:=default}"
: "${CLI_AGENT_HISTORY_DIR:=${HOME}/.local/share/cli-agent}"

_cli_agent_history_file="${CLI_AGENT_HISTORY_DIR}/${CLI_AGENT_SESSION}/nl_history.txt"
_cli_agent_nl_history=()
_cli_agent_nl_index=0
_cli_agent_shell_hist_offset=0
_cli_agent_history_mode="shell"

_cli_agent_debug() {
  [[ -z "${CLI_AGENT_DEBUG_KEYS:-}" ]] && return
  local key="$1"
  local mode="$2"
  printf 'cli-agent key: %s (%s)\n' "$key" "$mode" >&2
}

_cli_agent_bind_key() {
  local sequence="$1"
  local handler="$2"
  bind -x "\"${sequence}\":${handler}" 2>/dev/null || true
  bind -m vi-insert -x "\"${sequence}\":${handler}" 2>/dev/null || true
  bind -m vi-command -x "\"${sequence}\":${handler}" 2>/dev/null || true
}

_cli_agent_prompt_reset() {
  _cli_agent_shell_hist_offset=0
  _cli_agent_nl_index=${#_cli_agent_nl_history[@]}
  _cli_agent_history_mode="shell"
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

_cli_agent_select_history_mode() {
  local prefix="${CLI_AGENT_PREFIX}"
  if [[ "$READLINE_LINE" == "${prefix}"* ]]; then
    _cli_agent_history_mode="nl"
    return
  fi
  if [[ -n "$READLINE_LINE" ]]; then
    _cli_agent_history_mode="shell"
  fi
}

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

_cli_agent_history_up() {
  local prefix="${CLI_AGENT_PREFIX}"
  _cli_agent_select_history_mode
  if [[ "${_cli_agent_history_mode}" == "nl" ]]; then
    _cli_agent_debug "up" "nl"
    _cli_agent_shell_hist_offset=0
    if (( _cli_agent_nl_index > 0 )); then
      ((_cli_agent_nl_index--))
      READLINE_LINE="${prefix}${_cli_agent_nl_history[_cli_agent_nl_index]}"
    else
      READLINE_LINE="${prefix}"
    fi
    READLINE_POINT=${#READLINE_LINE}
    return
  fi

  _cli_agent_debug "up" "shell"
  local limit=${HISTCMD:-0}
  if (( _cli_agent_shell_hist_offset < limit )); then
    ((_cli_agent_shell_hist_offset++))
    local entry
    entry=$(builtin history -p "!-${_cli_agent_shell_hist_offset}" 2>/dev/null)
    entry=${entry%$'\n'}
    if [[ -n "${entry}" ]]; then
      READLINE_LINE="${entry}"
      READLINE_POINT=${#READLINE_LINE}
    fi
  fi
}

_cli_agent_history_down() {
  local prefix="${CLI_AGENT_PREFIX}"
  _cli_agent_select_history_mode
  if [[ "${_cli_agent_history_mode}" == "nl" ]]; then
    _cli_agent_debug "down" "nl"
    _cli_agent_shell_hist_offset=0
    local total=${#_cli_agent_nl_history[@]}
    if (( _cli_agent_nl_index < total )); then
      ((_cli_agent_nl_index++))
      if (( _cli_agent_nl_index == total )); then
        READLINE_LINE="${prefix}"
      else
        READLINE_LINE="${prefix}${_cli_agent_nl_history[_cli_agent_nl_index]}"
      fi
    else
      READLINE_LINE="${prefix}"
    fi
    READLINE_POINT=${#READLINE_LINE}
    return
  fi

  _cli_agent_debug "down" "shell"
  if (( _cli_agent_shell_hist_offset > 1 )); then
    ((_cli_agent_shell_hist_offset--))
    local entry
    entry=$(builtin history -p "!-${_cli_agent_shell_hist_offset}" 2>/dev/null)
    entry=${entry%$'\n'}
    READLINE_LINE="${entry}"
    READLINE_POINT=${#READLINE_LINE}
  elif (( _cli_agent_shell_hist_offset == 1 )); then
    _cli_agent_shell_hist_offset=0
    READLINE_LINE=""
    READLINE_POINT=0
  fi
}

_cli_agent_bind_key "\\e[A" _cli_agent_history_up
_cli_agent_bind_key "\\eOA" _cli_agent_history_up
_cli_agent_bind_key "\\e[B" _cli_agent_history_down
_cli_agent_bind_key "\\eOB" _cli_agent_history_down

_cli_agent_restore_enter() {
  case "$(bind -X 2>/dev/null)" in
    *"_cli_agent_accept_line"*)
      bind '"\C-m": accept-line'
      bind '"\C-j": accept-line'
      bind -m vi-insert '"\C-m": accept-line'
      bind -m vi-insert '"\C-j": accept-line'
      bind -m vi-command '"\C-m": vi-accept-line'
      bind -m vi-command '"\C-j": vi-accept-line'
      ;;
  esac
}

_cli_agent_restore_enter
unset -f _cli_agent_accept_line 2>/dev/null || true

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
    printf '\n'
    _cli_agent_run_payload "${payload}"
    _cli_agent_shell_hist_offset=0
    if ((HISTCMD)); then
      history -d $((HISTCMD - 1)) >/dev/null 2>&1 || true
    fi
    return 0
  fi

  if declare -f _cli_agent_prev_command_not_found_handle >/dev/null 2>&1; then
    _cli_agent_prev_command_not_found_handle "$cmd" "$@"
    return $?
  fi

  printf 'bash: %s: command not found\n' "$cmd" >&2
  return 127
}

CLI_AGENT_PLUGIN_LOADED=1
