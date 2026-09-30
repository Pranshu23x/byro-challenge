from app.checks import check_draft, parse_prohibited
from app.models import Draft


def test_prohibited_claim_blocks_draft(synthetic_prohibited):
    entries = parse_prohibited(synthetic_prohibited)
    assert {e[0] for e in entries} == {"P1", "P2"}

    bad = Draft(id="d1", text="we will double revenue next quarter", angle="claim")
    check_draft(bad, post_text="we shipped a dashboard", profile_text="",
                evidence_text="", prohibited_entries=entries, accepted_rules=[])
    assert bad.blocked, "prohibited phrase must block the draft"
    assert any(f.kind == "prohibited" and f.severity == "block" for f in bad.flags)

    ok = Draft(id="d2", text="been waiting for this one, nice", angle="ack")
    check_draft(ok, post_text="we shipped a dashboard", profile_text="",
                evidence_text="", prohibited_entries=entries, accepted_rules=[])
    assert not ok.blocked
    assert not any(f.kind == "prohibited" for f in ok.flags)


def test_unsupported_number_is_flagged(synthetic_prohibited, synthetic_evidence):
    entries = parse_prohibited(synthetic_prohibited)

    d = Draft(id="d1", text="we grew 300% in a month", angle="claim")
    check_draft(d, post_text="we shipped a dashboard", profile_text="",
                evidence_text=synthetic_evidence, prohibited_entries=entries,
                accepted_rules=[])
    assert any(f.kind == "number" for f in d.flags), \
        "a number absent from post+evidence must be flagged"
    assert not d.blocked, "number findings warn, they do not block"

    d2 = Draft(id="d2", text="5 people shipping this is wild", angle="ack")
    check_draft(d2, post_text="we are 5 people on the team now", profile_text="",
                evidence_text=synthetic_evidence, prohibited_entries=entries,
                accepted_rules=[])
    assert not any(f.kind == "number" for f in d2.flags), \
        "numbers present in the post are allowed"


def test_blocked_draft_cannot_be_approved(decisions_file, tmp_path):
    from app.review import approve
    proposal = {"post_id": "p1", "post_text": "post"}
    draft = {"id": "p1-d1", "text": "revenue will explode",
             "flags": [{"kind": "prohibited", "severity": "block", "detail": "x"}]}
    try:
        approve(proposal, draft, decisions_path=decisions_file,
                handoff_path=tmp_path / "handoff.jsonl")
    except PermissionError:
        assert not decisions_file.exists(), "blocked draft must not be recorded"
        return
    raise AssertionError("approve() should refuse a blocked draft")
