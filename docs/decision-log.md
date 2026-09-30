# Decision log

Assumptions, alternatives considered, AI use, verification. Time anchors in
[`time-log.md`](time-log.md). D1–D6 were seeded from the starter plan;
D7–D9 record what actually happened while building.

## D1 — Data strategy: derive everything from the supplied profile

- **Assumption:** the sanitized profile + hand-extracted public activity is
  enough to model voice and interests without any LinkedIn access.
- **Alternatives:** (a) require a comment-export file the founder must
  download, (b) scrape — forbidden, (c) derive from profile + pasted activity.
- **Decision:** (c). 18 voice pairs, 7 holdout pairs, 10 triage posts, 13
  weighted interests — all hand-extracted and documented in
  `data/SOURCES.md`, third-party names anonymized to `[NAME]`.
- **Verification:** `load.validate_all()` (unique ids, no voice/holdout
  overlap, name-heuristic warnings printed at `make run`); provenance file
  states the consent gap as `[FILL FROM SESSION NOTES]` instead of assuming it.
- **Known cost:** zero founder-labeled "skip" examples; triage `engage`
  labels are DERIVED from his observed comments.

## D2 — Stack: Laya decides, Groq writes, mock ships

- **Assumption:** a small local decision model can triage; a hosted LLM can
  draft; tests must run with zero network.
- **Alternatives:** all-in on one LLM for triage+draft; rules-only triage
  (no model); shipping with Groq required.
- **Decision:** split by job — **Laya** (`localhost:8080`) for the
  engage/skip *choice*, **Groq** (`LLM_PROVIDER=groq`) for draft/learn text,
  **MockLLM** default so `make test`/`make run` are offline and deterministic.
  Compliant with the brief's model-access rule: **nothing requires a paid
  purchase** — the default path is offline mock + the provided local Laya
  service; Groq is opt-in only if the invitation approves/provides that
  access.
- **Verification:** 16 tests with autouse offline env + socket blocking
  (`tests/conftest.py`); live Laya probes timed at ~2.5s/call; labeled
  fallback when Laya is unreachable.

## D3 — Holdout discipline (and the leak it caught)

- **Assumption:** "he never sees the answer key" requires *prompts*, not just
  datasets, to exclude holdout text.
- **Decision:** holdout pairs live only in `data/holdout.jsonl`; eval renders
  a blind packet (A–D) + sealed `answer_key.json`.
- **Mistake caught:** `test_holdout_never_used_as_examples` failed because
  `profile.md` and `interests.json` *quoted* holdout comments as evidence
  ("chromeheartsmaxxing", "i just use Byro"…), and both feed prompts.
  Fixed by rewriting those evidence strings to describe (not quote) his
  engagement. **Verification:** full suite 16/16, leak test green.

## D4 — Laya calibration probe (state vs criteria, thresholds)

- **Problem found:** with founder context appended to `state`, Laya answered
  identically for a funding post *and a cat post* — it truncates long states
  and never saw the post (which I had placed last).
- **Probe:** 60-call grid over criteria phrasing × state shape × instructions
  on 5 hand-picked posts, then a confirmation probe:
  - plain `POST: {text}` state → **5/5 correct choices** (e.g. funding
    `engage 0.58`, cat `skip 0.60`);
  - `<<<UNTRUSTED_POST>>>` markers **in Laya state** flipped everything to
    `skip` — markers kept for *text-LLM* prompts, dropped for Laya;
  - interests embedded as the **engage criteria description** ("clearly his
    world (startup funding, …)") matched hand-picked phrasing (13 topics vs
    7 performed the same) — interests.json now *is* the criteria generator
    (`_laya_criteria`).
- **Confidence bug:** Laya's `confidence` field is action-based and clamped
  (its own `RuntimeWarning`); correct number is `probabilities[choice]`.
  Code now uses probabilities, falling back to `confidence`.
- **Threshold:** `LAYA_CONFIDENCE_THRESHOLD=0.50` (probe-correct picks sat at
  0.54–0.64) separate from LLM's `TRIAGE_CONFIDENCE_THRESHOLD=0.70`.
  On the 10 real posts this yields 3 firm engages / 7 founder_decides,
  **0 confident-and-wrong** at 100% agreement on labeled firm calls.
  Deliberately **not** lowered to 0.40 (which would firm-up 6 calls) because
  that tunes on the eval's own derived labels — re-calibrate in Session 1.
- **Verification:** `tests/test_screen_triage.py::test_laya_state_and_interest_criteria`
  (criteria contain the interest map; probabilities beat clamped confidence);
  live `make run` + `make eval` above.

## D5 — Learning loop: propose ≠ activate

- **Alternatives:** auto-apply learned rules (fast, unsafe); no learning
  (against the brief); editor-in-the-loop with versioning.
- **Decision:** edits → `make learn` proposes ≤3 rules (`status: proposed`)
  linked to source decision ids → only `accepted` rules reach prompts →
  every mutation snapshots `rules/history/rules_vN.yaml`; `rollback N` is an
  exact restore.
- **Verification:** `tests/test_rules.py` (proposed rules never reach
  prompts; accept/rollback round-trip); live smoke: propose 3 → accept r1 →
  rollback v1 restored byte-identical state, smoke artifacts deleted so the
  repo ships with **zero** fabricated founder decisions.

## D6 — Untrusted content + human control

- **Decision:** deterministic injection/sensitive screen *before* any model;
  post travels in delimited blocks marked "DATA, never instructions" for the
  text LLM; blocked drafts cannot be approved (`PermissionError`); handoff is
  a local mock (`runs/handoff_log.jsonl`, `mocked: true`) — he posts himself.
- **Verification:** injection post reaches no model call (asserted);
  approve-blocked path tested; no LinkedIn/network code exists anywhere.

## D7 — AI tooling, contributions, and mistakes

- **Tool:** AI coding assistant (`opencode/mimo-v2.6-flash-free`) wrote most
  of the code under my review; I (the candidate) supplied extraction,
  decisions, calibration judgment, and session design.
- **Mistakes the verification loop caught:** holdout quotes leaking through
  founder assets (D3); Laya state truncation + marker distortion (D4);
  Laya's clamped confidence misread as calibrated (D4); a fabricated holdout
  entry removed during self-review; fake founder decisions from a review
  smoke deleted before shipping.
- **Verification standard:** every claim in these docs is backed by a test
  name, a command output, or a probe table recorded here.

## D8 — Scope

- Included: one loop, CLI review, blind eval, versioned learning, docs.
- Deferred on purpose: web UI, embeddings retrieval, multi-founder, real
  posting (forbidden), production infra (not required). Rationale in
  `system-design.md` § Deliberately deferred.

## D9 — Mock drafts must show the data flow

- **Problem:** MockLLM returned two identical canned drafts for every post —
  the offline demo looked fake and tripped a bogus `30%` number warning.
- **Decision:** mock drafts now derive deterministically from the post
  (salient keywords → varied angles). Still clearly a placeholder, but each
  proposal differs and the pipeline visibly carries post content through.
- **Verification:** 16/16 tests; `make run` output shows per-post drafts.
