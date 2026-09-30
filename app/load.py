"""Read + validate local data fixtures. No network, no LinkedIn access."""
import json
import os
import re
from pathlib import Path

from app.models import HoldoutExample, TriageItem, VoiceExample

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# crude heuristic: two capitalised words that are not sentence-initial and not
# common English openers. Warn-only; documented as noisy in the design doc.
_NAME_RE = re.compile(r"(?<![.\n!?]\s)\b([A-Z][a-z]+) ([A-Z][a-z]+)\b")
_NON_NAMES = {
    "The And", "New York", "San Francisco", "LinkedIn", "New Post",
    "My Big", "Same Model", "Today We", "Get Merch",
}


class DataError(Exception):
    pass


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise DataError(f"missing data file: {path}")
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise DataError(f"{path.name}:{i} is not valid JSON: {e}") from e
    return rows


def _require(row: dict, keys: list[str], where: str):
    for k in keys:
        if k not in row or (isinstance(row[k], str) and not row[k].strip()):
            raise DataError(f"{where}: missing required field {k!r}")


def _check_unique_ids(rows: list[dict], where: str):
    seen = set()
    for r in rows:
        if r.get("id") in seen:
            raise DataError(f"{where}: duplicate id {r.get('id')!r}")
        seen.add(r.get("id"))


def warn_possible_names(text: str) -> list[str]:
    hits = []
    for m in _NAME_RE.finditer(text):
        pair = m.group(0)
        if pair in _NON_NAMES:
            continue
        hits.append(pair)
    return hits


def load_voice_examples(path: Path | None = None) -> list[VoiceExample]:
    rows = _read_jsonl(path or (DATA / "voice_examples.jsonl"))
    for r in rows:
        _require(r, ["id", "post_text", "founder_comment"], "voice_examples")
    _check_unique_ids(rows, "voice_examples")
    return [VoiceExample(
        id=r["id"], post_text=r["post_text"], founder_comment=r["founder_comment"],
        topic=r.get("topic", "")) for r in rows]


def load_holdout(path: Path | None = None) -> list[HoldoutExample]:
    rows = _read_jsonl(path or (DATA / "holdout.jsonl"))
    for r in rows:
        _require(r, ["id", "post_text", "founder_comment"], "holdout")
    _check_unique_ids(rows, "holdout")
    return [HoldoutExample(
        id=r["id"], post_text=r["post_text"], founder_comment=r["founder_comment"],
        topic=r.get("topic", "")) for r in rows]


def load_triage_posts(path: Path | None = None) -> list[TriageItem]:
    rows = _read_jsonl(path or (DATA / "triage_posts.jsonl"))
    for r in rows:
        _require(r, ["id", "post_text"], "triage_posts")
    _check_unique_ids(rows, "triage_posts")
    return [TriageItem(
        id=r["id"], post_text=r["post_text"],
        founder_label=r.get("founder_label"),
        founder_reason=r.get("founder_reason", "")) for r in rows]


def load_own_posts(path: Path | None = None) -> list[dict]:
    rows = _read_jsonl(path or (DATA / "founder" / "own_posts.jsonl"))
    for r in rows:
        _require(r, ["id", "text"], "own_posts")
    return rows


def load_text(relpath: str) -> str:
    p = DATA / relpath
    if not p.exists():
        raise DataError(f"missing data file: {p}")
    return p.read_text(encoding="utf-8")


def load_interests() -> dict:
    raw = load_text("founder/interests.json")
    return json.loads(raw)


def validate_all(warn_names: bool = True) -> list[str]:
    """Full intake validation. Returns list of warnings; raises DataError on hard
    failures: missing fields, duplicate ids, voice/holdout id OR text overlap."""
    warnings: list[str] = []
    voice = load_voice_examples()
    holdout = load_holdout()
    load_triage_posts()
    load_own_posts()
    load_text("founder/profile.md")
    load_text("founder/evidence.md")
    load_text("founder/prohibited.md")
    load_interests()

    voice_ids = {v.id for v in voice}
    overlap = voice_ids & {h.id for h in holdout}
    if overlap:
        raise DataError(f"holdout overlaps voice_examples ids: {sorted(overlap)}")
    voice_texts = {v.post_text for v in voice}
    text_overlap = voice_texts & {h.post_text for h in holdout}
    if text_overlap:
        raise DataError("holdout shares post_text with voice_examples (leakage)")

    if not voice:
        raise DataError("voice_examples is empty")
    if not holdout:
        warnings.append("holdout is empty — blind test will be empty")

    if warn_names:
        for v in voice + holdout:
            for hit in warn_possible_names(v.post_text)[:2]:
                warnings.append(
                    f"possible real name in {v.id} post_text: {hit!r} (heuristic; verify by hand)")
    return warnings


if __name__ == "__main__":
    for w in validate_all():
        print("WARN:", w)
    print("data OK")
