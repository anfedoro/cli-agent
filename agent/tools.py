from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List


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
]


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
    except Exception as exc:
        return f"{name} failed: {exc}"
    return f"Unknown tool: {name}"
