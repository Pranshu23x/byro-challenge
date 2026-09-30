"""MOCK handoff. Writes a local log line and tells the founder to paste the
comment into LinkedIn himself. No network calls of any kind — ever."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HANDOFF_PATH = ROOT / "runs" / "handoff_log.jsonl"


def log_approval(decision_row: dict, path: Path | None = None) -> dict:
    p = path or HANDOFF_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": decision_row.get("ts"),
        "post_id": decision_row.get("post_id"),
        "draft_id": decision_row.get("draft_id"),
        "text": decision_row.get("final_text") or decision_row.get("original_text", ""),
        "action": decision_row.get("action"),
    }
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def handoff_message(post_id: str, post_text: str, text: str) -> str:
    ref = post_text[:60].replace("\n", " ")
    return (
        "\n--- COPY AND POST THIS YOURSELF ---\n"
        f"post reference: {post_id} — \"{ref}…\"\n\n"
        f"{text}\n"
        "-----------------------------------\n"
        "No network action was taken. Open LinkedIn, find the post, paste, done.\n"
    )


def print_handoff(post_id: str, post_text: str, text: str) -> None:
    print(handoff_message(post_id, post_text, text))
