"""Tests for the arrow-key browse CLI (app/browse.py).

The engine takes injectable read_key/copy/approve/skip functions, so the
whole interaction (navigation, select, pause, quit) runs offline with no
real terminal, no real clipboard, and no writes to the real runs/ dir.
"""
import json

from app.browse import browse_cli, format_case, ranked_drafts, run_browse
from app.review import approve, record_decision


def _prop(post_id="t01", texts=("alpha comment", "beta comment", "gamma comment"),
          scores=None, rec=None, blocked_idx=(), status="drafted"):
    drafts = []
    for i, t in enumerate(texts, 1):
        d = {"id": f"{post_id}-d{i}", "text": t, "angle": "ack", "flags": []}
        if i in blocked_idx:
            d["flags"].append({"kind": "prohibited", "severity": "block",
                               "detail": "claim"})
        drafts.append(d)
    return {"post_id": post_id, "post_text": "we shipped something nice",
            "status": status, "screen": {}, 
            "triage": {"decision": "engage", "backend": "laya",
                       "reason": "laya: engage", "confidence": 0.8},
            "drafts": drafts, "reasons": [],
            "recommended": rec, "judge": "test note",
            "scores": scores or {}}


def _keys(seq):
    it = iter(seq)
    return lambda: next(it)


def _approver(tmp_path):
    dp = tmp_path / "decisions.jsonl"
    hp = tmp_path / "handoff.jsonl"

    def fn(prop, draft):
        return approve(prop, draft, reason="test", decisions_path=dp,
                       handoff_path=hp)
    return fn, dp, hp


def test_ranked_drafts_score_order_star_first_blocked_last():
    prop = _prop(scores={"t01-d1": 0.5, "t01-d2": 1.5, "t01-d3": 0.9},
                 rec="t01-d2", blocked_idx=(3,))
    ids = [d["id"] for d in ranked_drafts(prop)]
    assert ids == ["t01-d2", "t01-d1", "t01-d3"]


def test_ranked_drafts_without_scores_keeps_order_recommended_first():
    prop = _prop(rec="t01-d3")
    ids = [d["id"] for d in ranked_drafts(prop)]
    assert ids == ["t01-d3", "t01-d1", "t01-d2"]


def test_format_case_shows_rank_star_selector_and_scores():
    prop = _prop(scores={"t01-d1": 0.42, "t01-d2": 1.18}, rec="t01-d2")
    out = format_case(prop, 1, 0, 3)
    assert "Case 1/3" in out
    assert "★" in out and out.index("★") < out.index("  [3]")  # star on ranked line
    assert "► " in out  # selector marker
    assert "score 1.18" in out and "score 0.42" in out
    assert "judge: test note" in out
    assert "up/down" in out.replace("\u2191/\u2193", "up/down")


def test_format_case_marks_blocked():
    prop = _prop(blocked_idx=(2,))
    out = format_case(prop, 0, 0, 1)
    assert "[BLOCKED]" in out


def test_select_copies_logs_approves_and_advances(tmp_path, capsys):
    prop = _prop(scores={"t01-d1": 0.4, "t01-d2": 1.2}, rec="t01-d2")
    prop2 = _prop(post_id="t02")
    copied = []
    fn, dp, hp = _approver(tmp_path)
    keys = _keys(["enter", "x", "enter", "x"])  # select+pause on each case
    stats = run_browse([prop, prop2], read_key=keys, copy_fn=copied.append,
                       approve_fn=fn, skip_fn=lambda p: None, write=lambda *a: None)
    assert stats["selected"] == 2 and not stats["quit"]
    assert copied == ["beta comment", "alpha comment"]  # ★ first on t01
    rows = [json.loads(l) for l in dp.read_text(encoding="utf-8").splitlines()]
    assert [r["action"] for r in rows] == ["approve", "approve"]
    assert [r["post_id"] for r in rows] == ["t01", "t02"]
    assert hp.exists() and "approve" in hp.read_text(encoding="utf-8")


def test_blocked_draft_cannot_be_selected(tmp_path):
    prop = _prop(texts=("good", "bad claim"), scores={"t01-d1": 0.1},
                 blocked_idx=(2,))
    copied, approved = [], []
    out = []
    # down to the blocked one, enter (refused), then quit
    keys = _keys(["down", "enter", "q"])
    stats = run_browse([prop], read_key=keys, copy_fn=copied.append,
                       approve_fn=lambda p, d: approved.append(d),
                       skip_fn=lambda p: None, write=out.append)
    assert stats["selected"] == 0 and copied == [] and approved == []
    assert any("blocked" in line for line in out)
    assert stats["quit"]


def test_skip_logs_and_advances(tmp_path):
    prop = _prop()
    recorded = []
    keys = _keys(["s", "x"])  # skip + pause -> ends (only case)
    stats = run_browse([prop], read_key=keys, copy_fn=lambda t: True,
                       approve_fn=lambda p, d: None,
                       skip_fn=lambda p: recorded.append(p["post_id"]),
                       write=lambda *a: None)
    assert stats["skipped"] == 1 and recorded == ["t01"]


def test_navigation_and_back():
    p1, p2 = _prop(post_id="t01"), _prop(post_id="t02")
    seen = []
    keys = _keys(["left", "n", "left", "n", "q"])  # left@first refused, fwd, back, fwd, quit
    stats = run_browse([p1, p2], read_key=keys, copy_fn=lambda t: True,
                       approve_fn=lambda p, d: None, skip_fn=lambda p: None,
                       write=lambda *a: None, clear=None)
    assert stats["quit"] and stats["selected"] == 0


def test_copy_failure_still_approves(tmp_path):
    prop = _prop()
    fn, dp, hp = _approver(tmp_path)
    out = []
    keys = _keys(["enter", "x"])
    stats = run_browse([prop], read_key=keys, copy_fn=lambda t: False,
                       approve_fn=fn, skip_fn=lambda p: None, write=out.append)
    assert stats["selected"] == 1
    assert dp.exists()
    assert any("clipboard failed" in m for m in out)


def test_default_approve_and_skip_would_use_real_paths_is_avoided(tmp_path):
    """Engine defaults exist but tests always inject — assert injection works."""
    called = {"approve": 0, "skip": 0}
    prop = _prop()
    keys = _keys(["s", "x"])
    stats = run_browse([prop], read_key=keys, copy_fn=lambda t: True,
                       approve_fn=lambda p, d: called.__setitem__("approve", 1),
                       skip_fn=lambda p: called.__setitem__("skip", 1),
                       write=lambda *a: None)
    assert called == {"approve": 0, "skip": 1}


def test_browse_cli_non_interactive_lists_cases(tmp_path, capsys):
    path = tmp_path / "proposals.jsonl"
    rows = [_prop(), _prop(post_id="t02", status="skipped")]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    rc = browse_cli(path=path, interactive=False)
    out = capsys.readouterr().out
    assert rc == 0
    assert "Case 1/1" in out  # skipped case filtered out
    assert "static listing" in out


def test_browse_cli_empty(tmp_path, capsys):
    rc = browse_cli(path=tmp_path / "nope.jsonl", interactive=False)
    assert rc == 0
    assert "nothing to browse" in capsys.readouterr().out
