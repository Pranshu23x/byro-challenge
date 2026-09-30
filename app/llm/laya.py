"""HTTP client for the local Laya decision service (triage backend).

Laya scores decision options; it does not generate text. Request shape is the
one documented by the service: POST /decide {state, questions} where questions
are {qid: {type, instructions, criteria}}; answers come back as
{qid: {choice, confidence, ...}}.

If the service is unreachable the caller falls back to the LLM backend.
"""
import os

import requests

LAQA_TIMEOUT = 30


class LayaClient:
    def __init__(self, url: str | None = None, timeout: int = LAQA_TIMEOUT):
        self.url = (url or os.getenv("LAYA_URL", "http://localhost:8080")).rstrip("/")
        self.timeout = timeout

    def healthy(self) -> bool:
        try:
            r = requests.get(f"{self.url}/health", timeout=3)
            return r.status_code == 200 and r.json().get("status") == "ok"
        except (requests.RequestException, ValueError):
            return False

    def decide(self, state: str, questions: dict) -> dict | None:
        """Return answers dict, or None when the service is unavailable/fails."""
        try:
            r = requests.post(
                f"{self.url}/decide",
                json={"state": state, "questions": questions},
                timeout=self.timeout,
            )
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError):
            return None
        answers = data.get("answers")
        return answers if isinstance(answers, dict) else None
