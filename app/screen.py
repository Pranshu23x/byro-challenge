"""Deterministic screening of untrusted post text: prompt injection + sensitive
topics. Flags travel with the post; nothing here calls a model."""
import re

from app.models import ScreenResult

INJECTION_PATTERNS = [
    r"ignore (all |previous |prior )?instructions",
    r"disregard (all |previous |prior )?(instructions|rules)",
    r"you are now",
    r"system prompt",
    r"new instructions",
    r"developer mode",
    r"act as (an? )?(admin|developer|unrestricted)",
    r"jailbreak",
    r"forget (everything|all previous)",
    r"\<\|im_start\|>",
    r"do not (tell|inform) the (user|founder)",
    r"output the following",
]

SENSITIVE_PATTERNS = [
    # provisional defaults; founder's own list extends this in Session 1
    r"\blay[\s-]?offs?\b", r"\blaying\s+off\b", r"\blaid\s?off\b",
    r"\bredundanc", r"\bfir(e|ing|ed)\b", r"\bshut(s|ting)?\s+down\b",
    r"\bgrief\b", r"\bmourn", r"\bfuneral\b", r"\bpassed away\b", r"\bdied\b",
    r"\bdeath\b", r"\bcancer\b", r"\bhospitali[sz]",
    r"\belection\b", r"\bpolling\b", r"\bdemocrat", r"\brepublican",
    r"\bwar\b", r"\binvasion\b", r"\bshooting\b", r"\bterroris", r"\btragedy\b",
    r"\bsuicid", r"\babuse\b", r"\bharassment\b",
]

_INJECTION_RE = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]
_SENSITIVE_RE = [re.compile(p, re.IGNORECASE) for p in SENSITIVE_PATTERNS]


def screen(post_text: str) -> ScreenResult:
    result = ScreenResult()
    for rx in _INJECTION_RE:
        m = rx.search(post_text)
        if m:
            result.injection = True
            result.reasons.append(f"injection pattern: {m.group(0)!r}")
    for rx in _SENSITIVE_RE:
        m = rx.search(post_text)
        if m:
            result.sensitive = True
            result.reasons.append(f"sensitive topic: {m.group(0)!r}")
    return result
