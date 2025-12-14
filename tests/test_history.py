from pathlib import Path

from agent.history import HistoryStore


def test_history_append_and_reset(tmp_path):
    store = HistoryStore(tmp_path, "demo")

    store.append_chat({"role": "user", "content": "hello"})
    store.append_nl_command("do something")

    messages = store.load_chat_messages()
    assert messages[0] == {"role": "user", "content": "hello"}

    nl_content = store.nl_path.read_text(encoding="utf-8").strip()
    assert nl_content == "do something"

    store.reset()
    assert store.chat_path.read_text(encoding="utf-8") == ""
    assert store.nl_path.read_text(encoding="utf-8") == ""


def test_history_records_tool_calls_as_text(tmp_path):
    store = HistoryStore(tmp_path, "demo")
    store.reset()

    store.append_chat(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "1",
                    "type": "function",
                    "function": {"name": "list_dir", "arguments": '{"path": "./"}', "extra": "x"},
                    "extra": "ignored",
                }
            ],
            "refusal": None,
            "audio": None,
        }
    )
    store.append_chat({"role": "assistant", "content": "done"})

    messages = store.load_chat_messages()
    assert messages == [
        {"role": "assistant", "content": 'Tool: list_dir({"path": "./"})'},
        {"role": "assistant", "content": "done"},
    ]

    raw = store.chat_path.read_text(encoding="utf-8")
    assert "tool\t" in raw


def test_load_chat_compacts_legacy_json(tmp_path):
    store = HistoryStore(tmp_path, "demo")
    store.reset()

    legacy = '\n'.join(
        [
            '{"role": "user", "content": "hi"}',
            '{"role": "assistant", "content": null, "tool_calls": [{"id": "1", "type": "function", "function": {"name": "list_dir", "arguments": "{\\"path\\": \\"./\\"}"}}]}',
            '{"role": "tool", "tool_call_id": "1", "name": "list_dir", "content": ".\\nREADME.md"}',
            '{"role": "assistant", "content": "done"}',
        ]
    )
    store.chat_path.write_text(legacy, encoding="utf-8")

    messages = store.load_chat_messages()

    assert messages == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": 'Tool: list_dir({"path": "./"})'},
        {"role": "assistant", "content": "done"},
    ]

    rewritten = store.chat_path.read_text(encoding="utf-8")
    assert rewritten.strip().splitlines() == [
        'user\t"hi"',
        'tool\t"list_dir({\\"path\\": \\"./\\"})"',
        'assistant\t"done"',
    ]
