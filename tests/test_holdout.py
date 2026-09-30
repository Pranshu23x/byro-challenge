import app.load as load_mod
import app.pipeline as pipeline
import app.retrieve as retrieve_mod
import inspect
from app.llm.mock import MockLLM
from app.models import Post


def test_holdout_never_used_as_examples(monkeypatch):
    # 1. the retrieval module never imports or loads holdout data
    src = inspect.getsource(retrieve_mod)
    assert "load_holdout" not in src
    assert "holdout" not in src.replace("never holdout.jsonl (enforced by test).", "")

    # 2. distinctive holdout comments, read up front for later comparison
    holdout_comments = [h.founder_comment for h in load_mod.load_holdout()]
    distinctive = [c for c in holdout_comments if len(c) > 8]
    assert distinctive, "need at least one distinctive holdout comment"

    # 3. loading holdout during drafting is an error
    def _explode(*a, **k):
        raise AssertionError("holdout.jsonl was read during drafting")

    monkeypatch.setattr(load_mod, "load_holdout", _explode)

    llm = MockLLM()
    prop = pipeline.run_one(
        Post("hp1", "we shipped a new dashboard for small teams"), llm,
        backend="llm")
    assert prop.status in ("drafted", "founder_decides", "blocked")

    # 4. no holdout comment text appears in any prompt the model received
    prompt_blob = "\n".join(c["system"] + c["user"] for c in llm.calls)
    for c in distinctive:
        assert c not in prompt_blob, f"holdout comment leaked into prompt: {c!r}"
