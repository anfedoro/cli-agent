from __future__ import annotations

import asyncio
import json
import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text content to a file, creating parent directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Target file path"},
                    "content": {"type": "string", "description": "Text content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file and return its content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_cmd",
            "description": "Execute a shell command locally (e.g. pwd, ls, cat) and return stdout/stderr/exit code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string", "description": "Command to execute"},
                },
                "required": ["cmd"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": "Request clarification from the user. Should return a question in plain text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Question to ask the user"},
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_config",
            "description": "Show the active cli-agent configuration (toml) and its path.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_config_value",
            "description": "Update a configuration key and persist it to disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Dotted key path, e.g. provider.model or provider.model_params.reasoning_effort",
                    },
                    "value": {"type": "string", "description": "New value (JSON or raw string)"},
                },
                "required": ["path", "value"],
            },
        },
    },
]

_ACTIVE_CONFIG_PATH: Optional[Path] = None


async def _write_file(path: str, content: str) -> str:
    target = Path(path).expanduser()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"wrote {target}"
    except Exception as exc:
        return f"write_file failed: {exc}"


async def _read_file(path: str) -> str:
    target = Path(path).expanduser()
    try:
        return target.read_text(encoding="utf-8")
    except Exception as exc:
        return f"read_file failed: {exc}"


async def _run_cmd(cmd: str) -> str:
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await process.communicate()
        except asyncio.CancelledError:
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=2)
            except Exception:
                process.kill()
            raise
        result = {
            "cmd": cmd,
            "exit_code": process.returncode,
            "stdout": stdout_bytes.decode("utf-8", errors="ignore"),
            "stderr": stderr_bytes.decode("utf-8", errors="ignore"),
        }
        return json.dumps(result)
    except Exception as exc:
        return json.dumps({"cmd": cmd, "error": str(exc)})


async def _ask_user(question: str) -> str:
    # CLI is non-interactive; return the question so it can be surfaced to the user.
    return question


def set_active_config_path(path: Optional[Path]) -> None:
    global _ACTIVE_CONFIG_PATH
    _ACTIVE_CONFIG_PATH = path


def _toml_value(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        inner = ", ".join(f"{k} = {_toml_value(v)}" for k, v in value.items())
        return "{ " + inner + " }"
    return json.dumps(value)


def _dump_config_toml(data: Dict[str, Any]) -> str:
    sections: List[Tuple[str, Dict[str, Any]]] = []
    for key in ("provider", "agent", "prompt", "ui", "tools"):
        if key in data and isinstance(data[key], dict):
            sections.append((key, data[key]))

    lines: List[str] = []

    # Root keys (for legacy flat files)
    root_keys = {k: v for k, v in data.items() if not isinstance(v, dict)}
    for k, v in root_keys.items():
        lines.append(f"{k} = {_toml_value(v)}")
    if root_keys:
        lines.append("")

    for name, section in sections:
        lines.append(f"[{name}]")
        for k, v in section.items():
            if isinstance(v, dict):
                lines.append(f"[{name}.{k}]")
                for nk, nv in v.items():
                    lines.append(f"{nk} = {_toml_value(nv)}")
                lines.append("")
            else:
                lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")

    return "\n".join(line for line in lines if line.strip() != "" or line == "")


def _load_config_for_tools() -> Tuple[Optional[Path], Optional[Dict[str, Any]]]:
    if not _ACTIVE_CONFIG_PATH:
        return None, None
    try:
        content = _ACTIVE_CONFIG_PATH.read_bytes()
        data = tomllib.loads(content.decode("utf-8"))
        return _ACTIVE_CONFIG_PATH, data
    except Exception:
        return _ACTIVE_CONFIG_PATH, None


def _set_config_value(path: str, raw_value: str) -> str:
    cfg_path, data = _load_config_for_tools()
    if not cfg_path:
        return "No active config path available."
    if data is None:
        return f"Failed to load config from {cfg_path}"

    parts = path.split(".")
    cursor: Any = data
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    try:
        parsed_value = json.loads(raw_value)
    except json.JSONDecodeError:
        parsed_value = raw_value

    cursor[parts[-1]] = parsed_value

    try:
        cfg_path.write_text(_dump_config_toml(data), encoding="utf-8")
    except Exception as exc:
        return f"Failed to write config: {exc}"

    return f"Updated {path} in {cfg_path}"


def _show_config() -> str:
    cfg_path, data = _load_config_for_tools()
    if not cfg_path:
        return "No active config path available."
    if data is None:
        return f"Failed to load config from {cfg_path}"
    return f"path: {cfg_path}\n\n{_dump_config_toml(data)}"


async def execute_tool_call(tool_call: Dict[str, Any]) -> str:
    name = tool_call.get("function", {}).get("name")
    args_raw = tool_call.get("function", {}).get("arguments", "{}") or "{}"
    try:
        args = json.loads(args_raw)
    except json.JSONDecodeError:
        return f"Invalid arguments for {name}: {args_raw}"

    try:
        if name == "write_file":
            return await _write_file(args.get("path", ""), args.get("content", ""))
        if name == "read_file":
            return await _read_file(args.get("path", ""))
        if name == "run_cmd":
            return await _run_cmd(args.get("cmd", ""))
        if name == "ask_user":
            return await _ask_user(args.get("question", ""))
        if name == "show_config":
            return _show_config()
        if name == "set_config_value":
            return _set_config_value(args.get("path", ""), args.get("value", ""))
    except Exception as exc:
        return f"{name} failed: {exc}"
    return f"Unknown tool: {name}"
