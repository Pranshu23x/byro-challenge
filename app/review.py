"""Founder review loop: approve / edit / reject / skip. Decisions are
append-only; blocked drafts cannot be approved."""
import datetime as _dt
import json
from pathlib import Path

from app import handoff
from app.models import Draft, Proposal

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
PROPOSALS_PATH = RUNS / "proposals.jsonl"
DECISIONS_PATH = RUNS / "decisions.jsonl"


def write_proposals(proposals: list[Proposal], path: Path | None = None) -> Path:
    p = path or PROPOSALS_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:  # proposals are regenerated, not history
        for prop in proposals:
            f.write(json.dumps(prop.to_dict(), ensure_ascii=False) + "\n")
    return p


def read_proposals(path: Path | None = None) -> list[Proposal]:
    p = path or PROPOSALS_PATH
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        out.append(json.loads(line))
    return out


def record_decision(action: str, post_id: str, draft_id: str,
                    original_text: str = "", final_text: str = "",
                    reason: str = "", path: Path | None = None) -> dict:
    """Append-only. Never rewrites an existing line."""
    if action not in {"approve", "edit", "reject", "skip"}:
        raise ValueError(f"unknown action {action!r}")
    row = {
        "ts": _dt.datetime.now().isoformat(timespec="seconds"),
        "post_id": post_id,
        "draft_id": draft_id,
        "action": action,
        "original_text": original_text,
        "final_text": final_text or original_text,
        "reason": reason,
    }
    p = path or DECISIONS_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:  # append only
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def approve(proposal: dict, draft: dict, reason: str = "",
            decisions_path: Path | None = None, handoff_path: Path | None = None) -> dict:
    if any(fl.get("severity") == "block" for fl in draft.get("flags", [])):
        raise PermissionError("draft is blocked by a prohibited-claim flag; cannot approve")
    row = record_decision("approve", proposal["post_id"], draft["id"],
                          original_text=draft["text"], final_text=draft["text"],
                          reason=reason, path=decisions_path)
    handoff.log_approval(row, path=handoff_path)
    return row


def edit(proposal: dict, draft: dict, new_text: str, reason: str = "",
         decisions_path: Path | None = None, handoff_path: Path | None = None) -> dict:
    row = record_decision("edit", proposal["post_id"], draft["id"],
                          original_text=draft["text"], final_text=new_text,
                          reason=reason, path=decisions_path)
    handoff.log_approval(row, path=handoff_path)
    return row


# ---------------------------------------------------------------- CLI ----

def _fmt_draft(i: int, d: dict, recommended: str | None = None) -> str:
    star = " ★ LAYA'S PICK —" if d.get("id") == recommended else ""
    lines = [f"  [{i}]{star} ({d.get('angle', '?')}) {d.get('text', '')!r}  id={d.get('id')}"]
    for fl in d.get("flags", []):
        lines.append(f"       FLAG [{fl['severity']}/{fl['kind']}] {fl['detail']}")
    if any(fl.get("severity") == "block" for fl in d.get("flags", [])):
        lines.append("       BLOCKED — cannot be approved")
    return "\n".join(lines)


def review_cli() -> None:
    from app.judge import order_drafts

    proposals = [p for p in read_proposals()
                 if p.get("status") in ("drafted", "blocked", "founder_decides")]
    pending = [p for p in proposals if p.get("drafts")]
    if not pending:
        print("nothing to review (run `make run` first).")
        return
    for prop in pending:
        tri = prop.get("triage") or {}
        print("\n" + "=" * 70)
        print(f"POST {prop['post_id']}  [{prop['status']}]  "
              f"triage={tri.get('decision')} ({tri.get('backend')}): {tri.get('reason')}")
        if prop.get("judge"):
            print(f"  judge: {prop['judge']}")
        print(f"  {prop['post_text'][:400]}{'…' if len(prop['post_text']) > 400 else ''}")
        prop = dict(prop)
        prop["drafts"] = order_drafts(prop["drafts"], prop.get("recommended"),
                                      prop.get("scores"))
        for i, d in enumerate(prop["drafts"], 1):
            print(_fmt_draft(i, d, prop.get("recommended")))
        print("  actions: approve <n> | edit <n> | reject <n> [reason] | skip | quit")
        while True:
            try:
                cmd = input("> ").strip()
            except EOFError:
                print(); return
            if cmd in ("quit", "q"):
                return
            if cmd == "skip":
                record_decision("skip", prop["post_id"], "")
                break
            parts = cmd.split(" ", 2)
            verb = parts[0]
            try:
                idx = int(parts[1]) - 1
                draft = prop["drafts"][idx]
            except (IndexError, ValueError):
                print("  usage: approve|edit|reject <draft#> [reason]"); continue
            reason = parts[2] if len(parts) > 2 else ""
            try:
                if verb == "approve":
                    approve(prop, draft, reason=reason)
                    print("  approved -> logged for handoff (post it yourself).")
                    break
                elif verb == "edit":
                    new = input("  new text> ").strip()
                    if not new:
                        print("  empty edit ignored."); continue
                    edit(prop, draft, new, reason=reason or "edited by founder")
                    print("  edited -> logged for handoff (post it yourself).")
                    break
                elif verb == "reject":
                    record_decision("reject", prop["post_id"], draft["id"],
                                    original_text=draft.get("text", ""), reason=reason)
                    print("  rejected.")
                    break
                else:
                    print("  unknown action")
            except PermissionError as e:
                print(f"  {e}")
