"""Voice rules: proposed from founder edits, accepted/rejected by the founder,
versioned, reversible. Only `accepted` rules ever reach a drafting prompt."""
import datetime as _dt
import json
from pathlib import Path

import yaml

from app.llm.base import BaseLLM, LLMError
from app.models import Draft

ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = ROOT / "rules" / "rules.yaml"
HISTORY_DIR = ROOT / "rules" / "history"


def load_rules(path: Path | None = None) -> dict:
    p = path or RULES_PATH
    if not p.exists():
        return {"version": 1, "rules": []}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    data.setdefault("version", 1)
    data.setdefault("rules", [])
    return data


def save_rules(data: dict, path: Path | None = None, snapshot: bool = True) -> None:
    p = path or RULES_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                 encoding="utf-8")
    if snapshot:
        hist = p.parent / "history"
        hist.mkdir(parents=True, exist_ok=True)
        snap = hist / f"rules_v{data['version']}.yaml"
        snap.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")


def accepted_rules(path: Path | None = None) -> list[dict]:
    return [r for r in load_rules(path)["rules"] if r.get("status") == "accepted"]


def accepted_statements(path: Path | None = None) -> list[str]:
    return [r.get("statement", "") for r in accepted_rules(path) if r.get("statement")]


def _next_version(data: dict) -> int:
    return int(data.get("version", 1)) + 1


def _next_id(data: dict) -> str:
    used = {r.get("id") for r in data["rules"]}
    n = 1
    while f"r{n}" in used:
        n += 1
    return f"r{n}"


def propose_rules(edited_decisions: list[dict], llm: BaseLLM,
                   path: Path | None = None) -> list[dict]:
    """At most 3 proposed rules, each linked to the decisions that caused it."""
    if not edited_decisions:
        return []
    evidence = json.dumps([
        {
            "decision_id": d.get("draft_id"),
            "original": d.get("original_text", ""),
            "founder_version": d.get("final_text", ""),
            "reason": d.get("reason", ""),
        }
        for d in edited_decisions
    ], ensure_ascii=False)
    system = (
        "TASK=learn\n"
        "You turn a founder's comment edits into at most 3 reusable voice rules. "
        "Rules must be short, specific and where possible machine-checkable "
        "(include params like max_chars or banned_phrase when the edit shows a "
        "length or phrase preference). Output STRICT JSON: "
        "{\"rules\": [{\"statement\": \"...\", \"kind\": \"style\", "
        "\"params\": {\"max_chars\": 120}, \"source_decision_ids\": [\"...\"]}]} "
        "- params is optional; use {} when not applicable."
    )
    raw = llm.complete_json(system, evidence)
    rules_out = raw.get("rules") if isinstance(raw, dict) else None
    if not isinstance(rules_out, list):
        raise LLMError("learn: model returned no rules list")

    data = load_rules(path)
    created = []
    for r in rules_out[:3]:
        if not isinstance(r, dict) or not r.get("statement"):
            continue
        entry = {
            "id": _next_id(data),
            "statement": str(r["statement"]),
            "kind": str(r.get("kind", "style")),
            "status": "proposed",
            "params": r.get("params") if isinstance(r.get("params"), dict) else {},
            "source_decision_ids": [str(x) for x in
                                    (r.get("source_decision_ids") or [])],
            "created": _dt.datetime.now().isoformat(timespec="seconds"),
        }
        # ensure a fresh id for each new entry within this batch
        while any(x["id"] == entry["id"] for x in data["rules"]):
            entry["id"] = f"r{len(data['rules']) + len(created) + 1}"
            entry["id"] = _next_id({"rules": data["rules"] + created})
        data["rules"].append(entry)
        created.append(entry)
    if created:
        data["version"] = _next_version(data)
        save_rules(data, path)
    return created


def set_status(rule_id: str, status: str, path: Path | None = None) -> dict:
    data = load_rules(path)
    for r in data["rules"]:
        if r["id"] == rule_id:
            r["status"] = status
            data["version"] = _next_version(data)
            save_rules(data, path)
            return r
    raise KeyError(f"no rule with id {rule_id!r}")


def rollback(version: int, path: Path | None = None) -> dict:
    """Restore rules.yaml to the exact snapshot of `version`."""
    p = path or RULES_PATH
    snap = (p.parent / "history") / f"rules_v{version}.yaml"
    if not snap.exists():
        raise FileNotFoundError(f"no snapshot rules_v{version}.yaml")
    p.write_text(snap.read_text(encoding="utf-8"), encoding="utf-8")
    return load_rules(path)


def edited_decisions(decisions_path: Path) -> list[dict]:
    if not decisions_path.exists():
        return []
    out = []
    for line in decisions_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("action") == "edit":
            out.append(row)
    return out
