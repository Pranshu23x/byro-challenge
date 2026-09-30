"""Deterministic per-draft checks: prohibited phrases (block), unsupported
numbers/names (flag), repetition (flag), machine-checkable style rules (flag).
Heuristics are intentionally conservative: they flag for human review, they do
not claim to prove a claim is false."""
import difflib
import json
import re
from pathlib import Path

from app.models import Draft, Flag

NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?\s*%?|\b[$€£]\s?[\d.,]+|\b\d+x\b", re.IGNORECASE)
CAPWORD_RE = re.compile(r"\b([A-Z][a-zA-Z]{2,})\b")

_COMMON_CAPS = {
    "The", "This", "That", "What", "When", "Where", "Who", "How", "And", "But",
    "For", "You", "Your", "Our", "We", "He", "She", "They", "It", "His", "Her",
    "LinkedIn", "Post", "One", "Two", "Yes", "No", "Same", "Now", "So", "If",
    "In", "On", "At", "By", "A", "An", "I", "My", "Me",
}


def parse_prohibited(text: str) -> list[tuple[str, list[str], str]]:
    """Parse `P1 | [\"phrase\", ...] | reason` lines from prohibited.md."""
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("P"):
            continue
        parts = line.split(" | ")
        if len(parts) < 3:
            continue
        pid = parts[0].strip()
        try:
            phrases = json.loads(parts[1])
        except json.JSONDecodeError:
            phrases = [parts[1].strip()]
        if isinstance(phrases, str):
            phrases = [phrases]
        entries.append((pid, [str(p).lower() for p in phrases], parts[2]))
    return entries


def evidence_claims(evidence_text: str) -> list[str]:
    claims = []
    for line in evidence_text.splitlines():
        line = line.strip()
        if line.startswith("E") and "|" in line:
            claims.append(line)
    return claims


def check_draft(
    draft: Draft,
    post_text: str,
    profile_text: str,
    evidence_text: str,
    prohibited_entries: list[tuple[str, list[str], str]],
    accepted_rules: list[dict],
    prior_texts: list[str] | None = None,
) -> Draft:
    text = draft.text
    lower = text.lower()

    # 1. prohibited phrases -> block (never approvable)
    for pid, phrases, reason in prohibited_entries:
        for p in phrases:
            if p and p in lower:
                draft.flags.append(Flag(
                    kind="prohibited", severity="block",
                    detail=f"{pid}: matches {p!r} — {reason}"))
                break

    # 2. unsupported numbers: number/percent/currency not present in post or evidence
    allowed_text = f"{post_text}\n{evidence_text}"
    for m in NUMBER_RE.finditer(text):
        token = m.group(0).strip()
        core = token.replace(" ", "")
        if core in allowed_text.replace(" ", ""):
            continue
        draft.flags.append(Flag(
            kind="number", severity="warn",
            detail=f"{token!r} does not appear in the post or evidence.md"))

    # 3. capitalised words not known from post/profile/evidence (noisy heuristic)
    known = set(CAPWORD_RE.findall(post_text))
    known |= set(CAPWORD_RE.findall(profile_text))
    known |= set(CAPWORD_RE.findall(evidence_text))
    known |= set(CAPWORD_RE.findall(" ".join(evidence_claims(evidence_text))))
    body = text[1:] if text[:1].isupper() else text  # ignore sentence-initial
    for w in CAPWORD_RE.findall(body):
        if w in known or w in _COMMON_CAPS:
            continue
        draft.flags.append(Flag(
            kind="name", severity="warn",
            detail=f"capitalised word {w!r} not found in post/profile/evidence (heuristic)"))
        break  # one flag per draft is enough noise

    # 4. repetition vs his real examples and recently approved comments
    threshold = 0.85
    for other in list(prior_texts or []):
        if not other:
            continue
        ratio = difflib.SequenceMatcher(None, text.lower(), other.lower()).ratio()
        if ratio >= threshold:
            draft.flags.append(Flag(
                kind="repetition", severity="warn",
                detail=f"{ratio:.0%} similar to a previous comment"))
            break

    # 5. machine-checkable accepted style rules
    for rule in accepted_rules:
        params = rule.get("params") or {}
        if "max_chars" in params:
            limit = int(params["max_chars"])
            if len(text) > limit:
                draft.flags.append(Flag(
                    kind="style", severity="warn",
                    detail=f"rule {rule.get('id')}: {len(text)} chars > max_chars {limit}"))
        if "banned_phrase" in params:
            bp = str(params["banned_phrase"]).lower()
            if bp and bp in lower:
                draft.flags.append(Flag(
                    kind="style", severity="warn",
                    detail=f"rule {rule.get('id')}: contains banned phrase {bp!r}"))

    return draft


def prior_approved_texts(handoff_log_path: Path) -> list[str]:
    """Approved comment texts from the local handoff log (for repetition checks)."""
    if not handoff_log_path.exists():
        return []
    texts = []
    for line in handoff_log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = row.get("text")
        if isinstance(t, str):
            texts.append(t)
    return texts
