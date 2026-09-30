"""The primary flow, one post at a time:
screen -> triage -> retrieve -> draft -> checks -> Proposal."""
from pathlib import Path

from app.checks import check_draft, parse_prohibited, prior_approved_texts
from app.draft import draft
from app.handoff import HANDOFF_PATH
from app.llm.base import BaseLLM, LLMError
from app.load import load_text, load_voice_examples
from app.models import Post, Proposal, TriageResult
from app.retrieve import retrieve
from app.screen import screen
from app.triage import triage
from app import learn


def run_one(post: Post, llm: BaseLLM, backend: str | None = None,
            rules_path: Path | None = None) -> Proposal:
    scr = screen(post.text)
    try:
        tri: TriageResult = triage(post.text, scr, llm=llm, backend=backend)
    except LLMError as e:
        return Proposal(post_id=post.id, post_text=post.text, status="error",
                        screen=scr, triage=None,
                        reasons=[f"triage model error: {e}"])

    if tri.decision == "skip":
        return Proposal(post_id=post.id, post_text=post.text, status="skipped",
                        screen=scr, triage=tri, reasons=[tri.reason])

    examples = retrieve(load_voice_examples(), post.text)
    accepted = learn.accepted_rules(rules_path)
    statements = [r.get("statement", "") for r in accepted]

    try:
        drafts = draft(
            post_text=post.text, llm=llm,
            profile=load_text("founder/profile.md"),
            evidence=load_text("founder/evidence.md"),
            prohibited=load_text("founder/prohibited.md"),
            rules_statements=statements, examples=examples, post_id=post.id,
        )
    except LLMError as e:
        # model error / unparseable -> no draft, never a guessed one
        status = "founder_decides" if tri.decision == "founder_decides" else "error"
        return Proposal(post_id=post.id, post_text=post.text, status=status,
                        screen=scr, triage=tri,
                        reasons=[f"model error: {e}", tri.reason])

    prohibited_entries = parse_prohibited(load_text("founder/prohibited.md"))
    prior = prior_approved_texts(HANDOFF_PATH)
    for ex in examples:  # repetition against retrieved voice examples
        prior.append(ex.founder_comment)
    for d in drafts:
        check_draft(d, post.text, load_text("founder/profile.md"),
                    load_text("founder/evidence.md"), prohibited_entries,
                    accepted, prior_texts=prior)

    if not drafts:
        status = "blocked"
        reasons = ["no usable drafts returned"]
    elif all(d.blocked for d in drafts):
        status = "blocked"
        reasons = ["every draft blocked: " +
                   "; ".join(f.detail for d in drafts for f in d.flags
                             if f.severity == "block")]
    else:
        status = "drafted"
        reasons = [tri.reason]
    if tri.decision == "founder_decides" and status == "drafted":
        status = "founder_decides"
        reasons = ["triage uncertain — founder decides; drafts attached for convenience"]

    return Proposal(post_id=post.id, post_text=post.text, status=status,
                    screen=scr, triage=tri, drafts=drafts, reasons=reasons)
