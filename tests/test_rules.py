from app import learn
from app.draft import build_system_prompt


def test_only_accepted_rules_reach_prompt(tmp_rules):
    accepted = learn.accepted_rules(tmp_rules)
    assert [r["id"] for r in accepted] == ["r1"], "only status=accepted counts"

    statements = learn.accepted_statements(tmp_rules)
    sys_prompt = build_system_prompt("profile", "evidence", "prohibited",
                                     statements, [])
    assert "keep it under 120 chars" in sys_prompt
    assert "always open with a question" not in sys_prompt, \
        "proposed (unaccepted) rules must never reach a drafting prompt"

    # rejecting removes it from prompts too
    learn.set_status("r1", "rejected", path=tmp_rules)
    assert learn.accepted_statements(tmp_rules) == []


def test_rule_rollback_restores_previous_version(tmp_rules):
    # v1: r1 accepted (seeded by the fixture)
    learn.set_status("r1", "rejected", path=tmp_rules)  # -> v2
    data = learn.load_rules(tmp_rules)
    assert data["version"] == 2
    r1 = next(r for r in data["rules"] if r["id"] == "r1")
    assert r1["status"] == "rejected"
    assert (tmp_rules.parent / "history" / "rules_v2.yaml").exists()

    restored = learn.rollback(1, path=tmp_rules)  # exact restore of snapshot v1
    r1 = next(r for r in restored["rules"] if r["id"] == "r1")
    assert r1["status"] == "accepted", "rollback must restore prior status"
    assert learn.accepted_statements(tmp_rules) == ["keep it under 120 chars"]


def test_propose_rules_creates_proposed_entries(tmp_rules):
    from app.llm.mock import MockLLM
    edits = [{"draft_id": "p1-d1", "original_text": "great post, love it",
              "final_text": "love the red bull maths", "reason": "too generic"}]
    created = learn.propose_rules(edits, MockLLM(), path=tmp_rules)
    assert 1 <= len(created) <= 3, "at most 3 rules per proposal round"
    for r in created:
        assert r["status"] == "proposed", "new rules start as proposed"
        assert r["source_decision_ids"], "every rule links to source decisions"
    # proposed rules still do not reach prompts
    assert all(r["id"] == "r1" or r["status"] != "accepted"
               for r in learn.load_rules(tmp_rules)["rules"])
    assert "game changer" not in " ".join(
        learn.accepted_statements(tmp_rules))
