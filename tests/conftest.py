import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _offline_env(monkeypatch):
    """Tests run offline with the mock LLM and the llm triage backend."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("TRIAGE_BACKEND", "llm")
    monkeypatch.setenv("TRIAGE_CONFIDENCE_THRESHOLD", "0.70")


@pytest.fixture
def synthetic_voice():
    rows = [
        {"id": "s1", "post_text": "we shipped the new dashboard today",
         "founder_comment": "nice, been waiting for this", "topic": "product"},
        {"id": "s2", "post_text": "our seed round closed at last",
         "founder_comment": "congrats!", "topic": "funding"},
        {"id": "s3", "post_text": "hackathon winners announced",
         "founder_comment": "W", "topic": "community"},
    ]
    return rows


@pytest.fixture
def synthetic_prohibited():
    return (
        "# test prohibited\n"
        'P1 | ["revenue", "profitable"] | financial claims are not confirmed\n'
        'P2 | ["guaranteed"] | absolute claim\n'
    )


@pytest.fixture
def synthetic_evidence():
    return (
        "E1 | our team has five people | test source\n"
        "E2 | we were accepted into a validation programme | test source\n"
    )


@pytest.fixture(autouse=True)
def block_sockets(monkeypatch):
    """Fail loudly if any code under test opens a socket (handoff must be local)."""
    import socket

    def _blocked(*args, **kwargs):
        raise AssertionError("network call attempted in tests")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    yield


@pytest.fixture
def tmp_rules(tmp_path):
    """rules.yaml + history/ in a temp dir, seeded with v1 snapshot."""
    import yaml
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    data = {
        "version": 1,
        "rules": [
            {"id": "r1", "statement": "keep it under 120 chars", "kind": "style",
             "status": "accepted", "params": {"max_chars": 120},
             "source_decision_ids": ["d1"]},
            {"id": "r2", "statement": "always open with a question", "kind": "style",
             "status": "proposed", "params": {},
             "source_decision_ids": ["d2"]},
        ],
    }
    path = rules_dir / "rules.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    hist = rules_dir / "history"
    hist.mkdir()
    (hist / "rules_v1.yaml").write_text(path.read_text(encoding="utf-8"),
                                        encoding="utf-8")
    return path


@pytest.fixture
def proposals_file(tmp_path):
    return tmp_path / "proposals.jsonl"


@pytest.fixture
def decisions_file(tmp_path):
    return tmp_path / "decisions.jsonl"


def load_jsonl(path: Path) -> list:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()
            if x.strip()]
