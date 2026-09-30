from app import handoff
from app.review import approve, record_decision, write_proposals
from app.models import Draft, Proposal, ScreenResult, TriageResult


def test_decisions_log_is_append_only(decisions_file):
    record_decision("reject", "p1", "p1-d1", original_text="first",
                    reason="not my tone", path=decisions_file)
    prefix = decisions_file.read_bytes()

    record_decision("approve", "p1", "p1-d2", original_text="second",
                    path=decisions_file)

    after = decisions_file.read_bytes()
    assert after.startswith(prefix), "appending must never rewrite earlier lines"
    lines = after.splitlines()
    assert len(lines) == 2
    assert b'"first"' in lines[0]
    assert b'"second"' in lines[1]

    # appending again still leaves previous content untouched
    record_decision("skip", "p2", "", path=decisions_file)
    assert decisions_file.read_bytes().startswith(after)


def test_handoff_makes_no_network_calls(tmp_path, decisions_file):
    """Sockets are blocked by the conftest fixture — reaching the end of this
    test proves handoff only wrote a local file."""
    row = record_decision("approve", "p9", "p9-d1", original_text="nice one",
                          path=decisions_file)
    log = tmp_path / "handoff_log.jsonl"
    entry = handoff.log_approval(row, path=log)
    assert entry["text"] == "nice one"
    assert log.exists()

    msg = handoff.handoff_message("p9", "a post about shipping software", "nice one")
    assert "COPY AND POST THIS YOURSELF" in msg
    assert "No network action was taken" in msg


def test_approve_writes_local_log_only(tmp_path, decisions_file):
    proposal = {"post_id": "p3", "post_text": "we shipped"}
    draft = {"id": "p3-d1", "text": "been waiting for this", "angle": "ack",
             "flags": []}
    log = tmp_path / "handoff_log.jsonl"
    row = approve(proposal, draft, decisions_path=decisions_file,
                  handoff_path=log)
    assert row["action"] == "approve"
    assert log.read_text().count("\n") == 1


def test_write_and_read_proposals_roundtrip(tmp_path):
    p = tmp_path / "proposals.jsonl"
    prop = Proposal(post_id="x", post_text="post", status="drafted",
                    screen=ScreenResult(),
                    triage=TriageResult("engage", "ok", 0.9, "llm"),
                    drafts=[Draft(id="x-d1", text="hi", angle="ack")])
    write_proposals([prop], path=p)
    from app.review import read_proposals
    back = read_proposals(p)
    assert back[0]["status"] == "drafted"
    assert back[0]["drafts"][0]["text"] == "hi"
