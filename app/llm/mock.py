"""Deterministic offline LLM used by tests and as the default provider.

Behaviour is routed on the first line of the system prompt, which the
pipeline sets to `TASK=triage | draft | learn`. Tests inject canned outputs
via constructor arguments; nothing here touches the network.
"""
import re

from app.llm.base import BaseLLM, LLMError

# crude but deterministic: pull 1-2 salient words out of the post so each
# offline draft differs per post and visibly follows the data flow
_STOP = {
    "about", "after", "again", "being", "between", "could", "every", "first",
    "found", "great", "their", "there", "these", "those", "through", "under",
    "using", "what", "where", "which", "while", "would", "your", "people",
    "really", "just", "like", "some", "most", "from", "with", "have", "this",
    "that", "they", "them", "then", "than", "been", "were", "will", "into",
    "over", "only", "other", "more", "very", "also", "back", "when", "most",
    "takes", "take", "make", "made", "into", "here", "posts", "post", "long",
}


def _keywords(text: str, n: int = 2) -> list:
    words = set(re.findall(r"[a-zA-Z][a-zA-Z'-]{4,}", text.lower()))
    ranked = sorted((w for w in words if w not in _STOP),
                    key=lambda w: (-len(w), w))
    return ranked[:n]


class MockLLM(BaseLLM):
    def __init__(
        self,
        behavior: str = "normal",  # normal | error | unparseable
        triage: dict | None = None,
        triage_confidence: float | None = None,
        drafts: list | None = None,
        rules: list | None = None,
    ):
        self.behavior = behavior
        self._triage = triage
        self._triage_confidence = triage_confidence
        self._drafts = drafts
        self._rules = rules
        self.calls: list[dict] = []  # for assertions in tests

    def complete_json(self, system: str, user: str) -> dict:
        self.calls.append({"system": system, "user": user})
        if self.behavior == "error":
            raise LLMError("mock model error")
        if self.behavior == "unparseable":
            raise LLMError("mock unparseable output")

        task = "unknown"
        for line in system.splitlines()[:3]:
            if line.startswith("TASK="):
                task = line.split("=", 1)[1].strip()
                break

        if task == "triage":
            return self._triage_result()
        if task == "draft":
            return {"drafts": self._draft_list(user)}
        if task == "learn":
            return {"rules": self._rule_list()}
        raise LLMError(f"mock: no canned output for task {task!r}")

    def _triage_result(self) -> dict:
        if self._triage is not None:
            return self._triage
        conf = 0.9 if self._triage_confidence is None else self._triage_confidence
        decision = "engage" if conf >= 0.5 else "skip"
        return {
            "decision": decision,
            "reason": f"mock triage (confidence={conf})",
            "confidence": conf,
        }

    def _draft_list(self, user: str = "") -> list:
        if self._drafts is not None:
            return self._drafts
        post = ""
        if "<<UNTRUSTED_POST\n" in user and "\nUNTRUSTED_POST>>" in user:
            post = user.split("<<UNTRUSTED_POST\n", 1)[1].split("\nUNTRUSTED_POST>>", 1)[0]
        kws = _keywords(post)
        if not kws:
            return [
                {"text": "same, the boring middle is where products get made",
                 "angle": "shared-experience", "evidence_ids": []},
                {"text": "what was the hardest part for you here?",
                 "angle": "question", "evidence_ids": []},
            ]
        k1 = kws[0]
        drafts = [
            {"text": f"how did {k1} turn out for you in the end?",
             "angle": "question", "evidence_ids": []},
            {"text": f"{k1} done right is underrated",
             "angle": "shared-experience", "evidence_ids": []},
        ]
        if len(kws) > 1:
            drafts[1] = {"text": f"{kws[1]} rarely gets enough credit, nice one",
                         "angle": "ack", "evidence_ids": []}
        return drafts

    def _rule_list(self) -> list:
        if self._rules is not None:
            return self._rules
        return [
            {
                "statement": "keep comments under 120 characters",
                "kind": "style",
                "source_decision_ids": ["d1"],
            },
            {
                "statement": "banned_phrase: game changer",
                "kind": "style",
                "source_decision_ids": ["d2"],
            },
            {
                "statement": "prefer a playful jab over a generic compliment",
                "kind": "style",
                "source_decision_ids": ["d3"],
            },
        ]
