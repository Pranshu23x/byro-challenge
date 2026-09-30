"""Tests for the ★ recommendation step (app/judge.py).

Judge behavior on real Laya is probe-documented in decision-log D10; these
tests pin the CONTRACT: star only from real scores, never in tests without
an injected client, unavailable judge -> no star, human flow unaffected.
"""
import pytest

from app.judge import apply_judge, order_drafts, recommend_draft
from app.models import Draft, ScreenResult, TriageResult, Proposal
from app.screen import screen
from app.pipeline import run_one
from app.llm.mock import MockLLM


def _drafts(*texts, blocked_idx=()):
    out = []
    for i, t in enumerate(texts, 1):
        d = Draft(id=f"p1-d{i}", text=t, angle="a")
        if i in blocked_idx:
            from app.models import Flag
            d.flags.append(Flag(kind="prohibited", severity="block", detail="x"))
        out.append(d)
    return out


class FakeJudge:
    """Returns pre-programmed score sequences (one decide call per draft)."""

    def __init__(self, scores):
        self.scores = list(scores)
        self.calls = 0

    def decide(self, state, questions):
        self.calls += 1
        assert questions["fit"]["type"] == "score"
        assert "OPTION:" in state
        return {"fit": {"type": "score", "score": self.scores.pop(0)}}


def _laya_env(monkeypatch):
    monkeypatch.setenv("TRIAGE_BACKEND", "laya")
    monkeypatch.setenv("LAYA_JUDGE", "on")
    monkeypatch.delenv("LAYA_JUDGE_MIN_MARGIN", raising=False)


def test_recommends_highest_scoring_draft(monkeypatch):
    _laya_env(monkeypatch)
    drafts = _drafts("short one", "corporate two", "playful three")
    client = FakeJudge([0.4, 0.3, 1.2])
    prop = Proposal(post_id="p1", post_text="post", status="drafted",
                    screen=ScreenResult(), triage=None, drafts=drafts)
    apply_judge(prop, examples=[], client=client)
    assert prop.recommended == "p1-d3"
    assert client.calls == 3
    assert "margin" in prop.judge


def test_no_star_when_margin_too_small(monkeypatch):
    _laya_env(monkeypatch)
    monkeypatch.setenv("LAYA_JUDGE_MIN_MARGIN", "0.5")
    drafts = _drafts("a", "b")
    prop = Proposal(post_id="p1", post_text="post", status="drafted",
                    screen=ScreenResult(), triage=None, drafts=drafts)
    apply_judge(prop, examples=[], client=FakeJudge([1.0, 1.1]))
    assert prop.recommended is None
    assert "too close" in prop.judge


def test_judge_needs_two_clean_drafts(monkeypatch):
    _laya_env(monkeypatch)
    drafts = _drafts("clean", "bad", blocked_idx=(2,))
    client = FakeJudge([0.9])
    prop = Proposal(post_id="p1", post_text="post", status="drafted",
                    screen=ScreenResult(), triage=None, drafts=drafts)
    apply_judge(prop, examples=[], client=client)
    assert prop.recommended is None
    assert "2 clean drafts" in prop.judge
    assert client.calls == 0  # fewer than 2 clean drafts -> skip before scoring


def test_unavailable_judge_means_no_star_no_crash(monkeypatch):
    _laya_env(monkeypatch)

    class Down:
        def decide(self, state, questions):
            raise ConnectionError("service down")

    prop = Proposal(post_id="p1", post_text="post", status="drafted",
                    screen=ScreenResult(), triage=None,
                    drafts=_drafts("a", "b"))
    apply_judge(prop, examples=[], client=Down())
    assert prop.recommended is None
    assert "unavailable" in prop.judge


def test_judge_inactive_without_laya_backend(monkeypatch):
    monkeypatch.setenv("TRIAGE_BACKEND", "llm")  # conftest default
    client = FakeJudge([1.0, 1.0, 1.0])
    prop = Proposal(post_id="p1", post_text="post", status="drafted",
                    screen=ScreenResult(), triage=None,
                    drafts=_drafts("a", "b", "c"))
    apply_judge(prop, examples=[], client=client)
    assert prop.recommended is None
    assert client.calls == 0, "judge must not run when Laya is not the backend"


def test_judge_env_off(monkeypatch):
    monkeypatch.setenv("TRIAGE_BACKEND", "laya")
    monkeypatch.setenv("LAYA_JUDGE", "off")
    client = FakeJudge([1.0, 1.0])
    prop = Proposal(post_id="p1", post_text="post", status="drafted",
                    screen=ScreenResult(), triage=None, drafts=_drafts("a", "b"))
    apply_judge(prop, examples=[], client=client)
    assert prop.recommended is None and client.calls == 0


def test_blocked_proposal_never_judged(monkeypatch):
    _laya_env(monkeypatch)
    client = FakeJudge([1.0])
    prop = Proposal(post_id="p1", post_text="post", status="blocked",
                    screen=ScreenResult(), triage=None,
                    drafts=_drafts("a", blocked_idx=(1,)))
    apply_judge(prop, examples=[], client=client)
    assert prop.recommended is None and client.calls == 0


def test_order_drafts_puts_recommended_first():
    drafts = [{"id": "x"}, {"id": "r"}, {"id": "z"}]
    assert [d["id"] for d in order_drafts(drafts, "r")] == ["r", "x", "z"]
    assert order_drafts(drafts, None) == drafts
    objs = _drafts("a", "b")
    objs = order_drafts(objs, "p1-d2")
    assert objs[0].id == "p1-d2"


def test_review_marks_recommended_draft():
    from app.review import _fmt_draft
    d = {"id": "p1-d2", "text": "hi", "angle": "ack", "flags": []}
    assert "★ LAYA'S PICK" in _fmt_draft(1, d, "p1-d2")
    assert "★" not in _fmt_draft(1, d, "p1-d1")
    assert "★" not in _fmt_draft(1, d, None)


def test_run_one_pipeline_injects_judge(monkeypatch):
    """End-to-end: drafted proposal carries the star from an injected judge."""
    _laya_env(monkeypatch)
    prop = run_one(__import__("app.models", fromlist=["Post"]).Post(
        "t-judge", "we shipped the new dashboard for teams today"),
        MockLLM(), backend="llm",
        judge_client=FakeJudge([0.2, 1.1]))
    assert prop.status in ("drafted", "founder_decides")
    assert prop.recommended is not None
    assert prop.recommended.startswith("t-judge-d")
