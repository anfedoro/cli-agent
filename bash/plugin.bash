# Minimal bash integration for cli-agent

[[ -n "${BASH_VERSION:-}" ]] || return

: "${CLI_AGENT_PREFIX:=@}"
: "${CLI_AGENT_SESSION:=default}"
: "${CLI_AGENT_HISTORY_DIR:=${HOME}/.local/share/cli-agent}"

_cli_agent_history_file="${CLI_AGENT_HISTORY_DIR}/${CLI_AGENT_SESSION}/nl_history.txt"
_cli_agent_nl_history=()
_cli_agent_nl_index=0
_cli_agent_shell_hist_offset=0
declare -A _cli_agent_orig_bindings

_cli_agent_debug() {
  [[ -z "${CLI_AGENT_DEBUG_KEYS:-}" ]] && return
  local key="$1"
  local mode="$2"
  printf 'cli-agent key: %s (%s)\n' "$key" "$mode" >&2
}

_cli_agent_restore_sequence() {
  local sequence="$1"
  for mode in main vi-insert vi-command; do
    local key="${sequence}|${mode}"
    local val="${_cli_agent_orig_bindings[$key]}"
    if [[ "$mode" == "main" ]]; then
      bind -r "\"${sequence}\"" 2>/dev/null || true
      [[ -n "$val" ]] && bind ${val} 2>/dev/null || true
    else
      bind -m "${mode}" -r "\"${sequence}\"" 2>/dev/null || true
      [[ -n "$val" ]] && bind -m "${mode}" ${val} 2>/dev/null || true
    fi
  done
}

_cli_agent_bind_key() {
  local sequence="$1"
  local handler="$2"

  _cli_agent_orig_bindings["${sequence}|main"]="$(bind -v "\"${sequence}\"" 2>/dev/null || true)"
  _cli_agent_orig_bindings["${sequence}|vi-insert"]="$(bind -m vi-insert -v "\"${sequence}\"" 2>/dev/null || true)"
  _cli_agent_orig_bindings["${sequence}|vi-command"]="$(bind -m vi-command -v "\"${sequence}\"" 2>/dev/null || true)"

  bind -r "\"${sequence}\"" 2>/dev/null || true
  bind -m vi-insert -r "\"${sequence}\"" 2>/dev/null || true
  bind -m vi-command -r "\"${sequence}\"" 2>/dev/null || true

  local success=1
  bind -x "\"${sequence}\":${handler}" 2>/dev/null || success=0
  bind -m vi-insert -x "\"${sequence}\":${handler}" 2>/dev/null || success=0
  bind -m vi-command -x "\"${sequence}\":${handler}" 2>/dev/null || success=0

  if (( success == 0 )); then
    _cli_agent_restore_sequence "${sequence}"
  fi
}

_cli_agent_restore_bindings() {
  for seq_mode in "${!_cli_agent_orig_bindings[@]}"; do
    local seq="${seq_mode%%|*}"
    _cli_agent_restore_sequence "${seq}"
  done
}

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
    if [[ "$line" == ADD\ * ]]; then
      eval "${line#ADD }"
    fi
  done <<< "${output}"
  _cli_agent_refresh_history
}

_cli_agent_history_up() {
  local prefix="${CLI_AGENT_PREFIX}"
  local trimmed="${READLINE_LINE#"${READLINE_LINE%%[![:space:]]*}"}"
  if [[ "$trimmed" == "${prefix}" || "$trimmed" == "${prefix}"* ]]; then
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
  local trimmed="${READLINE_LINE#"${READLINE_LINE%%[![:space:]]*}"}"
  if [[ "$trimmed" == "${prefix}" || "$trimmed" == "${prefix}"* ]]; then
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

_cli_agent_accept_line() {
  local prefix="${CLI_AGENT_PREFIX}"
  if [[ "$READLINE_LINE" == "${prefix}"* ]]; then
    local payload="${READLINE_LINE#${prefix}}"
    printf '\n'
    _cli_agent_run_payload "${payload}"
    READLINE_LINE=""
    READLINE_POINT=0
    _cli_agent_shell_hist_offset=0
    if ((HISTCMD)); then
      history -d $((HISTCMD - 1)) >/dev/null 2>&1 || true
    fi
    READLINE_DONE=1
    return
  fi

  READLINE_DONE=1
  READLINE_POINT=${#READLINE_LINE}
}

_cli_agent_bind_key "\\C-m" _cli_agent_accept_line
_cli_agent_bind_key "\\C-j" _cli_agent_accept_line

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
