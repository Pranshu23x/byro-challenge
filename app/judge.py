"""Recommendation step: Laya picks a ★ draft, the human still decides.

Probe findings (docs/decision-log.md D10) — this module exists in spite of
them, per the founder's explicit choice:

- `choice` questions judge "is this a good comment?" and Laya's prior prefers
  polite full sentences over his terse style (inverted on his exact words).
- one multi-question call contaminates options (0/4).
- per-draft `score` questions ("how close to how he actually comments?")
  were the least-bad framing — still only ~1-2/4 on controlled probes.

So: the star is a SUGGESTION with published accuracy, never a gate. Anything
Laya-side failing means no star at all, never a random one.
"""
import os

from app.llm.laya import LayaClient
from app.models import Draft, Proposal

LEVELS = ["nothing like his comments", "somewhat like his comments",
          "exactly like his comments"]
INSTRUCTIONS = "How close is this option to how he actually comments on posts?"
POST_CLIP = 200  # Laya truncates long states (D4); style fit needs little post


def _judge_enabled() -> bool:
    if os.getenv("LAYA_JUDGE", "on").strip().lower() in ("off", "0", "false"):
        return False
    # only when Laya is already the active triage backend (keeps tests offline)
    return os.getenv("TRIAGE_BACKEND", "laya").strip().lower() == "laya"


def _min_margin() -> float:
    try:
        return float(os.getenv("LAYA_JUDGE_MIN_MARGIN", "0.05"))
    except ValueError:
        return 0.05


def _voice_line(examples) -> str:
    quotes = []
    for e in examples:
        text = getattr(e, "founder_comment", "") or ""
        if text and text not in quotes:
            quotes.append(text)
        if len(quotes) >= 4:
            break
    return "HIS REAL COMMENTS: " + " | ".join(f'"{q}"' for q in quotes) if quotes else ""


def _score_one(post_text: str, option: str, voice_line: str, client: LayaClient) -> float:
    parts = [f"POST: {post_text[:POST_CLIP]}"]
    if voice_line:
        parts.append(voice_line)
    parts.append(f"OPTION: \"{option}\"")
    state = "\n".join(parts)
    questions = {"fit": {"type": "score", "instructions": INSTRUCTIONS,
                         "criteria": LEVELS}}
    answers = client.decide(state, questions)
    if not answers or "fit" not in answers:
        raise ValueError("laya judge returned no answer")
    return float(answers["fit"]["score"])


def recommend_draft(post_text: str, drafts: list[Draft], examples,
                    client: LayaClient | None = None) -> tuple[str | None, dict, str]:
    """Return (recommended_draft_id | None, {draft_id: score}, note)."""
    usable = [d for d in drafts if not d.blocked]
    if len(usable) < 2:
        return None, {}, "judge skipped: fewer than 2 clean drafts"
    client = client or LayaClient()
    voice_line = _voice_line(examples)
    scores: dict[str, float] = {}
    try:
        for d in usable:
            scores[d.id] = _score_one(post_text, d.text, voice_line, client)
    except Exception as e:
        if isinstance(e, AssertionError):  # test guard must stay loud
            raise
        return None, scores, f"laya judge unavailable ({e.__class__.__name__})"
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top_id, top = ranked[0]
    margin = top - ranked[1][1]
    if margin < _min_margin():
        return None, scores, (f"judge too close to call "
                              f"(margin {margin:.3f} < {_min_margin():.2f})")
    return top_id, scores, f"laya pick by style-fit score (margin {margin:.3f})"


def apply_judge(prop: Proposal, examples, client: LayaClient | None = None) -> Proposal:
    """Attach a ★ recommendation to a drafted proposal. Never raises."""
    if prop.status not in ("drafted", "founder_decides") or not prop.drafts:
        return prop
    if not _judge_enabled():
        prop.judge = "judge off (LAYA_JUDGE/TRIAGE_BACKEND)"
        return prop
    try:
        rec, scores, note = recommend_draft(prop.post_text, prop.drafts,
                                            examples, client=client)
    except AssertionError:
        raise
    except Exception as e:
        rec, note = None, f"judge failed ({e.__class__.__name__})"
    prop.recommended = rec
    prop.judge = note
    return prop


def order_drafts(drafts: list, recommended: str | None) -> list:
    """Recommended first for display; stable otherwise. Works on dicts and
    Draft dataclasses."""
    if not recommended:
        return list(drafts)

    def _id(d):
        return d.get("id") if isinstance(d, dict) else getattr(d, "id", None)

    return sorted(drafts, key=lambda d: 0 if _id(d) == recommended else 1)
