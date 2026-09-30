"""Tests for the arrow-key browse CLI (app/browse.py).

The engine takes injectable read_key/copy/approve/skip/sleep functions, so
the whole interaction (Get Response -> loading -> pick -> copied, navigation,
skip, quit) runs offline with no real terminal, clipboard, or runs/ writes.
"""
import json

from app.browse import (browse_cli, format_copied, format_case,
                        format_loading, format_prompt, format_responses,
                        ranked_drafts, run_browse)
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


def test_prompt_shows_post_and_get_response_but_not_the_drafts():
    prop = _prop(scores={"t01-d1": 0.42}, rec="t01-d1")
    out = format_prompt(prop, 0, 3)
    assert "we shipped something nice" in out
    assert "[ Get Response ]" in out
    assert "Case 1 of 3" in out
    assert "alpha comment" not in out and "beta comment" not in out
    assert "canned data" in out  # honest label


def test_ui_has_no_internal_jargon():
    out = format_prompt(_prop(), 0, 1) + format_responses(_prop(), 0, 0, 1)
    low = out.lower()
    assert "laya" not in low and "judge" not in low
    assert "triage=" not in low and "status=" not in low
    assert "why:" not in low


def test_loading_frame_shows_spinner_no_drafts():
    prop = _prop()
    out = format_loading(prop, 0, 1, 3)
    assert "getting a response" in out
    assert "alpha comment" not in out


def test_responses_shows_rank_star_selector_and_scores():
    prop = _prop(scores={"t01-d1": 0.42, "t01-d2": 1.18}, rec="t01-d2")
    out = format_responses(prop, 1, 0, 3)
    assert "Re: we shipped something nice" in out
    assert "★" in out
    assert "► " in out
    assert "1.18" in out and "0.42" in out
    assert "choose" in out and "Enter" in out


def test_responses_marks_blocked():
    prop = _prop(blocked_idx=(2,))
    out = format_responses(prop, 0, 0, 1)
    assert "[BLOCKED]" in out


def test_copied_block_and_manual_fallback():
    ok = format_copied(True, "the text")
    assert "Copied to clipboard" in ok and "approved & logged" in ok
    fail = format_copied(False, "the text")
    assert "Clipboard unavailable" in fail and "the text" in fail


def test_get_response_then_select_copies_logs_and_advances(tmp_path):
    prop = _prop(scores={"t01-d1": 0.4, "t01-d2": 1.2}, rec="t01-d2")
    prop2 = _prop(post_id="t02")
    copied = []
    fn, dp, hp = _approver(tmp_path)
    # per case: enter (Get Response), enter (select), x (through confirmation)
    keys = ["enter", "enter", "x", "enter", "enter", "x"]
    stats = run_browse([prop, prop2], read_key=_keys(keys),
                       copy_fn=copied.append, approve_fn=fn,
                       skip_fn=lambda p: None, write=lambda *a: None,
                       sleep=lambda s: None)
    assert stats["selected"] == 2 and not stats["quit"]
    assert copied == ["beta comment", "alpha comment"]  # ★ first on t01
    rows = [json.loads(l) for l in dp.read_text(encoding="utf-8").splitlines()]
    assert [r["action"] for r in rows] == ["approve", "approve"]
    assert [r["post_id"] for r in rows] == ["t01", "t02"]
    assert hp.exists() and "approve" in hp.read_text(encoding="utf-8")


def test_responses_hidden_until_get_response_pressed():
    """Prompt + loading frames never render draft text; show frame does."""
    prop = _prop()
    frames = []
    keys = ["enter", "q"]
    stats = run_browse([prop], read_key=_keys(keys), copy_fn=lambda t: True,
                       approve_fn=lambda p, d: None, skip_fn=lambda p: None,
                       write=frames.append, sleep=lambda s: None)
    assert stats["quit"] and stats["selected"] == 0
    loads = [i for i, f in enumerate(frames) if "getting a response" in f]
    assert loads, "loading frame never rendered"
    for f in frames[:loads[-1] + 1]:
        assert "alpha comment" not in f
    assert any("alpha comment" in f for f in frames[loads[-1] + 1:])


def test_blocked_draft_cannot_be_selected(tmp_path):
    prop = _prop(texts=("good", "bad claim"), scores={"t01-d1": 0.1},
                 blocked_idx=(2,))
    copied, approved, out = [], [], []
    # load, down to blocked, enter refused (notice), quit
    keys = ["enter", "down", "enter", "q"]
    stats = run_browse([prop], read_key=_keys(keys), copy_fn=copied.append,
                       approve_fn=lambda p, d: approved.append(d),
                       skip_fn=lambda p: None, write=out.append,
                       sleep=lambda s: None)
    assert stats["selected"] == 0 and copied == [] and approved == []
    assert any("blocked" in line for line in out)
    assert stats["quit"]


def test_skip_logs_and_advances():
    prop = _prop()
    recorded = []
    keys = ["s", "x"]  # skip + pause -> ends (only case)
    stats = run_browse([prop], read_key=_keys(keys), copy_fn=lambda t: True,
                       approve_fn=lambda p, d: None,
                       skip_fn=lambda p: recorded.append(p["post_id"]),
                       write=lambda *a: None, sleep=lambda s: None)
    assert stats["skipped"] == 1 and recorded == ["t01"]


def test_navigation_and_back():
    p1, p2 = _prop(post_id="t01"), _prop(post_id="t02")
    keys = ["left", "n", "left", "n", "q"]
    stats = run_browse([p1, p2], read_key=_keys(keys), copy_fn=lambda t: True,
                       approve_fn=lambda p, d: None, skip_fn=lambda p: None,
                       write=lambda *a: None, clear=None,
                       sleep=lambda s: None)
    assert stats["quit"] and stats["selected"] == 0


def test_copy_failure_still_approves(tmp_path):
    prop = _prop()
    fn, dp, hp = _approver(tmp_path)
    out = []
    keys = ["enter", "enter", "x"]
    stats = run_browse([prop], read_key=_keys(keys), copy_fn=lambda t: False,
                       approve_fn=fn, skip_fn=lambda p: None, write=out.append,
                       sleep=lambda s: None)
    assert stats["selected"] == 1
    assert dp.exists()
    assert any("clipboard" in m.lower() for m in out)


def test_default_approve_and_skip_would_use_real_paths_is_avoided():
    """Engine defaults exist but tests always inject — assert injection works."""
    called = {"approve": 0, "skip": 0}
    prop = _prop()
    keys = ["s", "x"]
    stats = run_browse([prop], read_key=_keys(keys), copy_fn=lambda t: True,
                       approve_fn=lambda p, d: called.__setitem__("approve", 1),
                       skip_fn=lambda p: called.__setitem__("skip", 1),
                       write=lambda *a: None, sleep=lambda s: None)
    assert called == {"approve": 0, "skip": 1}


def test_browse_cli_non_interactive_lists_cases(tmp_path, capsys):
    path = tmp_path / "proposals.jsonl"
    rows = [_prop(), _prop(post_id="t02", status="skipped")]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    rc = browse_cli(path=path, interactive=False)
    out = capsys.readouterr().out
    assert rc == 0
    assert "Case 1 of 1" in out  # skipped case filtered out
    assert "static listing" in out
    assert "alpha comment" in out  # listing shows everything (no tty)


def test_browse_cli_empty(tmp_path, capsys):
    rc = browse_cli(path=tmp_path / "nope.jsonl", interactive=False)
    assert rc == 0
    assert "nothing to browse" in capsys.readouterr().out
