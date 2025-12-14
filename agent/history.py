from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class HistoryStore:
    base_dir: Path
    session: str

    def __post_init__(self) -> None:
        self.session_dir = self.base_dir.expanduser().resolve() / self.session
        self.chat_path = self.session_dir / "chat.jsonl"
        self.nl_path = self.session_dir / "nl_history.txt"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.chat_path.touch(exist_ok=True)
        self.nl_path.touch(exist_ok=True)

    def reset(self) -> None:
        """Truncate history files without deleting the session directory."""
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.chat_path.write_text("", encoding="utf-8")
        self.nl_path.write_text("", encoding="utf-8")

    def append_chat(self, message: Dict[str, Any]) -> None:
        """Append a simplified message to history as a single line."""
        lines = _message_to_history_lines(message)
        if not lines:
            return
        with self.chat_path.open("a", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

    def append_nl_command(self, command: str) -> None:
        command = command.strip("\n")
        if not command:
            return
        with self.nl_path.open("a", encoding="utf-8") as f:
            f.write(command + "\n")

    def load_chat_messages(self) -> List[Dict[str, Any]]:
        """Load chat messages from history as simple role/content pairs."""
        messages: List[Dict[str, Any]] = []
        raw_lines: List[str] = []
        canonical_lines: List[str] = []
        if not self.chat_path.exists():
            return messages
        with self.chat_path.open("r", encoding="utf-8") as f:
            for line in f:
                text = line.rstrip("\n")
                if not text:
                    continue
                raw_lines.append(text)
                if text.startswith("{"):
                    try:
                        loaded = json.loads(text)
                    except json.JSONDecodeError:
                        canonical_lines.append(text)
                        continue
                    canonical_lines.extend(_message_to_history_lines(loaded))
                    messages.extend(_message_to_simple_messages(loaded))
                elif "\t" in text:
                    parsed_messages = _history_line_to_messages(text)
                    if parsed_messages:
                        messages.extend(parsed_messages)
                    canonical_lines.append(text)
                else:
                    canonical_lines.append(text)

        if canonical_lines and canonical_lines != raw_lines:
            rewritten = "\n".join(canonical_lines) + "\n"
            self.chat_path.write_text(rewritten, encoding="utf-8")

        return messages


def _escape(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def _unescape(text: str) -> str:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _message_to_history_lines(message: Dict[str, Any]) -> List[str]:
    role = message.get("role")
    if not role:
        return []

    lines: List[str] = []

    if role == "assistant":
        tool_calls = message.get("tool_calls") or []
        for call in tool_calls:
            func = call.get("function", {}) if isinstance(call, dict) else {}
            name = func.get("name", "unknown")
            args = func.get("arguments", "")
            summary = f"{name}({args})" if args else name
            lines.append(f"tool\t{_escape(summary)}")
        content = message.get("content")
        if content not in (None, "", []):
            lines.append(f"assistant\t{_escape(str(content))}")
        return lines

    if role == "tool":
        # Do not store tool outputs; keep history concise.
        return []

    if role in ("user", "developer", "system"):
        content = message.get("content", "")
        lines.append(f"{role}\t{_escape(str(content))}")
        return lines

    # Fallback to JSON if unrecognized.
    return [json.dumps(message, ensure_ascii=False)]


def _message_to_simple_messages(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    role = message.get("role")
    if not role:
        return []

    if role == "assistant":
        simple: List[Dict[str, Any]] = []
        tool_calls = message.get("tool_calls") or []
        for call in tool_calls:
            func = call.get("function", {}) if isinstance(call, dict) else {}
            name = func.get("name", "unknown")
            args = func.get("arguments", "")
            summary = f"{name}({args})" if args else name
            simple.append({"role": "assistant", "content": f"Tool: {summary}"})
        content = message.get("content")
        if content not in (None, "", []):
            simple.append({"role": "assistant", "content": str(content)})
        return simple

    if role in ("user", "developer", "system"):
        return [{"role": role, "content": message.get("content", "")}]

    # Drop tool outputs entirely.
    if role == "tool":
        return []

    return [message]


def _history_line_to_messages(line: str) -> List[Dict[str, Any]]:
    if line.startswith("{"):
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError:
            return []
        return _message_to_simple_messages(loaded)

    if "\t" not in line:
        return []

    role, raw_content = line.split("\t", 1)
    content = _unescape(raw_content)

    if role == "tool":
        return [{"role": "assistant", "content": f"Tool: {content}"}]

    if role in ("user", "assistant", "developer", "system"):
        return [{"role": role, "content": content}]

    return []
