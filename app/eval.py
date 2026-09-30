"""The thin proof (`make eval`):
1. holdout blind packet — drafts and the founder's real comment, shuffled,
   for him to judge (answers the riskiest assumption directly)
2. triage agreement against his labels, including confident-and-wrong cases.
Both are DIRECTIONAL (n≈7–10), never statistical — stated in the report."""
import json
import random
from pathlib import Path

from app.llm.base import BaseLLM
from app.load import load_holdout, load_triage_posts
from app.models import Post
from app.pipeline import run_one
from app.triage import triage
from app.screen import screen

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"

LETTERS = "ABCD"


def build_holdout_packet(llm: BaseLLM, backend: str | None = None) -> dict:
    holdout = load_holdout()
    rng = random.Random(42)
    packet_lines = [
        "# Blind review packet — holdout set",
        "",
        "These posts were **never** used as voice examples while building. "
        "For each post: pick the comment you would actually send, say how much "
        "editing it needs, and mark which option is your real comment.",
        "",
        "Answer key is in `answer_key.json` — do not open it first.",
        "",
    ]
    key: dict = {}
    details: dict = {}
    stats = {"posts": 0, "with_draft": 0, "with_clean_draft": 0}

    for h in holdout:
        prop = run_one(Post(id=f"hold-{h.id}", text=h.post_text), llm, backend=backend)
        drafts = [d for d in (prop.drafts or []) if not d.blocked][:3]
        options = [d.text for d in drafts] + [h.founder_comment]
        letters = list(LETTERS[:len(options)])
        rng.shuffle(options)
        mapping = {}
        for letter, text in zip(letters, options):
            mapping[letter] = ("founder" if text == h.founder_comment else "draft")
        stats["posts"] += 1
        if drafts:
            stats["with_draft"] += 1
        if any(not d.flags for d in drafts):
            stats["with_clean_draft"] += 1

        key[h.id] = mapping
        details[h.id] = {
            "topic": h.topic,
            "status": prop.status,
            "drafts": [{"text": d.text, "angle": d.angle,
                        "flags": [{"kind": f.kind, "severity": f.severity,
                                   "detail": f.detail} for f in d.flags]}
                       for d in drafts],
            "founder_real_comment": h.founder_comment,
        }

        packet_lines += [f"## Post {h.id} (topic: {h.topic})", "",
                         "> " + h.post_text.replace("\n", "\n> "), "", ""]
        for letter, text in zip(letters, options):
            packet_lines.append(f"**{letter}.** {text}")
        packet_lines += ["",
                         "- Which would you send as-is? ___",
                         "- Which after light edits? ___",
                         "- Which would you never send, and why? ___",
                         "- Which one is yours? ___", ""]

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "review_packet.md").write_text(
        "\n".join(packet_lines), encoding="utf-8")
    (REPORTS / "answer_key.json").write_text(
        json.dumps(key, indent=2, ensure_ascii=False), encoding="utf-8")
    (REPORTS / "holdout_details.json").write_text(
        json.dumps(details, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"stats": stats, "key": key}


def triage_agreement(llm: BaseLLM, backend: str | None = None) -> dict:
    items = load_triage_posts()
    rows, labeled = [], 0
    confusion = {"engage->engage": 0, "engage->skip": 0, "skip->engage": 0,
                 "skip->skip": 0}
    confident_and_wrong = []

    for it in items:
        scr = screen(it.post_text)
        res = triage(it.post_text, scr, llm=llm, backend=backend)
        row = {"id": it.id, "system": res.decision, "backend": res.backend,
               "confidence": round(res.confidence, 2),
               "founder_label": it.founder_label,
               "founder_reason": it.founder_reason}
        rows.append(row)
        if it.founder_label in ("engage", "skip") and res.decision in ("engage", "skip"):
            labeled += 1
            confusion[f"{it.founder_label}->{res.decision}"] += 1
            if (res.decision != it.founder_label
                    and res.confidence >= 0.70):
                confident_and_wrong.append(row)

    correct = confusion["engage->engage"] + confusion["skip->skip"]
    return {
        "total_posts": len(items),
        "labeled": labeled,
        "agreement": (correct / labeled) if labeled else None,
        "confusion": confusion,
        "confident_and_wrong": confident_and_wrong,
        "rows": rows,
    }


def write_report(holdout_stats: dict, triage_result: dict) -> Path:
    lines = [
        "# Eval report",
        "",
        "> Directional, not statistical: ~7 holdout items and ~10 triage items",
        "> from a single founder's real activity. Treat as signal, not measurement.",
        "",
        "## Holdout blind test (the riskiest assumption)",
        f"- posts evaluated: {holdout_stats['posts']}",
        f"- posts with >= 1 non-blocked draft: {holdout_stats['with_draft']}",
        f"- posts with >= 1 draft passing ALL checks: {holdout_stats['with_clean_draft']}",
        "- founder judgments: **[FILL FROM SESSION 2 — see `session2_results.md`]**",
        "",
        "## Triage agreement",
        f"- labeled posts: {triage_result['labeled']} of {triage_result['total_posts']} "
        "(unlabeled rows are awaiting Session 1)",
        f"- agreement: "
        + (f"{triage_result['agreement']:.0%}"
           if triage_result["agreement"] is not None else "n/a (no labeled pairs yet)"),
        f"- confusion (founder->system): `{json.dumps(triage_result['confusion'])}`",
        "",
        "### Confident and wrong (system confidence >= 0.70 but disagreed)",
    ]
    if triage_result["confident_and_wrong"]:
        for r in triage_result["confident_and_wrong"]:
            lines.append(f"- {r['id']}: system={r['system']} ({r['confidence']}) "
                         f"vs founder={r['founder_label']} — {r['founder_reason']}")
    else:
        lines.append("- none in this run")
    lines += ["", "### Per-post rows",
              "```json", json.dumps(triage_result["rows"], indent=2), "```", ""]
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / "eval_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def run_eval(llm: BaseLLM, backend: str | None = None) -> dict:
    holdout_stats = build_holdout_packet(llm, backend)
    triage_result = triage_agreement(llm, backend)
    report = write_report(holdout_stats["stats"], triage_result)
    return {"holdout": holdout_stats["stats"], "triage": triage_result,
            "report": str(report)}
