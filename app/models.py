"""Core dataclasses shared across the pipeline. JSON via asdict()."""
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class VoiceExample:
    id: str
    post_text: str
    founder_comment: str
    topic: str = ""


@dataclass
class HoldoutExample:
    id: str
    post_text: str
    founder_comment: str
    topic: str = ""


@dataclass
class TriageItem:
    id: str
    post_text: str
    founder_label: Optional[str]  # engage | skip | None (awaiting Session 1)
    founder_reason: str = ""


@dataclass
class Post:
    id: str
    text: str


@dataclass
class ScreenResult:
    injection: bool = False
    sensitive: bool = False
    reasons: list[str] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.injection or self.sensitive


@dataclass
class TriageResult:
    decision: str  # engage | skip | founder_decides
    reason: str
    confidence: float
    backend: str  # rules | laya | llm | fallback


@dataclass
class Flag:
    kind: str  # prohibited | number | name | repetition | style
    severity: str  # block | warn
    detail: str


@dataclass
class Draft:
    id: str
    text: str
    angle: str
    evidence_ids: list[str] = field(default_factory=list)
    flags: list[Flag] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return any(f.severity == "block" for f in self.flags)


@dataclass
class Proposal:
    post_id: str
    post_text: str
    status: str  # skipped | founder_decides | drafted | blocked | error
    screen: ScreenResult
    triage: Optional[TriageResult]
    drafts: list[Draft] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    recommended: Optional[str] = None  # draft id Laya starred (suggestion only)
    judge: str = ""  # how/why the star was (or wasn't) assigned

    def to_dict(self) -> dict:
        return asdict(self)


def flag_to_dict(f: Flag) -> dict:
    return asdict(f)
