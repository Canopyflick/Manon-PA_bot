#!/usr/bin/env python3
"""Patch Nathan workflow backup JSON for image/OCR branch."""

from __future__ import annotations

import json
from pathlib import Path

BACKUP = Path(__file__).resolve().parent / "nathan-workflow-backup.json"
OUTPUT = Path(__file__).resolve().parent / "nathan-workflow-patched.json"

AGENT_TEXT = (
    "={{ $if(!!$('Telegram Trigger').item.json.message.voice, "
    "$('Set User Message (Voice)').item.json.userMessage, "
    "$if(!!($('Telegram Trigger').item.json.message.photo?.length || "
    "($('Telegram Trigger').item.json.message.document?.mime_type || '').startsWith('image/')), "
    "$('Set User Message (Photo)').item.json.userMessage, "
    "$('Set User Message (Text)').item.json.userMessage)) }}"
)

AGENT_SYSTEM = """=It is {{ $now }}. You are Nathan, a personal calendar assistant for Ben on Telegram. You manage Ben's **primary** Google Calendar (writable).

Capabilities:
- List Calendar Events: view upcoming events in a date range
- Create Calendar Event: add new events
- Delete Calendar Event: remove events by ID (always list first to confirm the right event)
- Read images: Ben may send photos of event posters, email screenshots, or invitations; you'll receive OCR text extracted from those images

Rules:
- Use Europe/Amsterdam timezone unless Ben specifies otherwise
- Be concise, Telegram messages should be short. Don't use markdown tables, those don't render
- Err on the side of just doing things, based on your best estimate, just relay whatever you did transparently and we can always undo/revert later. Only respond to a request with only questions if you can make no reasonable first-pass assumption at all
- Never invent events; only report what the tools return. If you're unsure about anything, just say so. Transparency is paramount and I know the setup can break and you can make mistakes, that's all fine. Let's experiment together, we're on the same team!
- When acting on OCR text from an image, mention briefly that you read it from a photo and flag anything ambiguous (unclear date/time/location)."""

CONNECTIONS = {
    "Telegram Trigger": {"main": [[{"node": "Filter", "type": "main", "index": 0}]]},
    "Calendar Agent": {"main": [[{"node": "Reply on Telegram", "type": "main", "index": 0}]]},
    "Chat Memory": {"ai_memory": [[{"node": "Calendar Agent", "type": "ai_memory", "index": 0}]]},
    "List Calendar Events": {"ai_tool": [[{"node": "Calendar Agent", "type": "ai_tool", "index": 0}]]},
    "Create Calendar Event": {"ai_tool": [[{"node": "Calendar Agent", "type": "ai_tool", "index": 0}]]},
    "Delete Calendar Event": {"ai_tool": [[{"node": "Calendar Agent", "type": "ai_tool", "index": 0}]]},
    "Send a chat action": {"main": [[{"node": "Calendar Agent", "type": "main", "index": 0}]]},
    "Filter": {"main": [[{"node": "Route Message Type", "type": "main", "index": 0}]]},
    "Route Message Type": {
        "main": [
            [{"node": "Get Telegram Voice File", "type": "main", "index": 0}],
            [{"node": "Resolve Image File", "type": "main", "index": 0}],
            [{"node": "Set User Message (Text)", "type": "main", "index": 0}],
        ]
    },
    "Transcribe Voice": {"main": [[{"node": "Set User Message (Voice)", "type": "main", "index": 0}]]},
    "Set User Message (Voice)": {"main": [[{"node": "Send a chat action", "type": "main", "index": 0}]]},
    "Set User Message (Text)": {"main": [[{"node": "Send a chat action", "type": "main", "index": 0}]]},
    "Set User Message (Photo)": {"main": [[{"node": "Send a chat action", "type": "main", "index": 0}]]},
    "Get Telegram Voice File": {"main": [[{"node": "Prepare Audio for Transcription", "type": "main", "index": 0}]]},
    "Resolve Image File": {"main": [[{"node": "Get Telegram Photo File", "type": "main", "index": 0}]]},
    "Get Telegram Photo File": {"main": [[{"node": "Prepare Image for Vision", "type": "main", "index": 0}]]},
    "Prepare Image for Vision": {"main": [[{"node": "Read Image", "type": "main", "index": 0}]]},
    "Read Image": {"main": [[{"node": "Set User Message (Photo)", "type": "main", "index": 0}]]},
    "Prepare Audio for Transcription": {"main": [[{"node": "Transcribe Voice", "type": "main", "index": 0}]]},
    "@preset/nathan": {"ai_languageModel": [[{"node": "Calendar Agent", "type": "ai_languageModel", "index": 0}]]},
}


def main() -> None:
    wf = json.loads(BACKUP.read_text(encoding="utf-8-sig"))
    nodes = [n for n in wf["nodes"] if n.get("name") != "Is Voice Note?"]
    for node in nodes:
        name = node.get("name")
        if name == "Calendar Agent":
            node["parameters"]["text"] = AGENT_TEXT
            node["parameters"]["options"]["systemMessage"] = AGENT_SYSTEM
        elif name == "Read Image":
            node["credentials"] = {
                "openRouterApi": {"id": "4MIbDJbXuh5LaFB9", "name": "OpenRouter Persoonlijk"}
            }
        elif name == "Get Telegram Photo File":
            node["credentials"] = {"telegramApi": {"id": "Y8dNzWhONz4j0aVP", "name": "Nathan"}}

    payload = {
        "name": wf["name"],
        "nodes": nodes,
        "connections": CONNECTIONS,
        "settings": {
            "executionOrder": wf.get("settings", {}).get("executionOrder", "v1"),
            "errorWorkflow": wf.get("settings", {}).get("errorWorkflow", "F8jhQSnsX59ZTYkQ"),
        },
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(nodes)} nodes)")


if __name__ == "__main__":
    main()
