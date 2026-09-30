# Design-partner feedback, limitations, next experiment

> Only verbatim partner input lands here. Until the sessions happen, every
> partner field is `[FILL FROM SESSION NOTES]` — no paraphrased or imagined
> reactions.

## Session 1 feedback — triage & boundaries

- Consent/provenance outcome: `[FILL FROM SESSION NOTES]`
- Triage labels agreed / disputed (with his reasons):
  `[FILL FROM SESSION NOTES — then rerun make eval]`
- Interest map changes he asked for: `[FILL FROM SESSION NOTES]`
- Evidence/prohibited edits: `[FILL FROM SESSION NOTES]`
- His words on when the system should stay quiet:
  `[FILL FROM SESSION NOTES — verbatim quotes only]`

## Session 2 feedback — blind draft judgments

**Prep before the session:** regenerate the packet with the real provider —
`LLM_PROVIDER=groq python -m app eval` — then hand over
`reports/review_packet.md`. Offline `mock` drafts are deliberately
placeholder text (D9); judging them proves nothing about voice quality.
One option per post is his *own real comment* (the discrimination test);
results must separate "would send a system draft" from "picked his own".

Result table lives in [`reports/session2_results.md`](../reports/session2_results.md)
(per-post A/B/C judgments, answer key untouched until he answers).

- Usable-without-edit rate: `[FILL FROM SESSION 2]`
- Recurring complaints: `[FILL FROM SESSION NOTES]`
- Did any draft feel "obviously AI"? `[FILL FROM SESSION NOTES]`
- Edit distance observed in `runs/decisions.jsonl`:
  `[FILL FROM SESSION NOTES]`

## Limitations (known now, before the sessions say them)

1. **n is tiny** — 7 holdout items, 10 triage items, one founder. Every
   number here is directional, not statistical (says so in the eval report).
2. **Labels are derived** — 9/10 triage labels inferred from comments he
   actually left; only Session 1 makes them his.
3. **Thresholds are probe-calibrated** — 0.50/0.70 chosen from a 5-post
   probe + sanity run, explicitly *not* tuned on the eval labels (that would
   contaminate the blind check). A wrong firm call in Session 1 is the
   trigger to revisit.
4. **Offline drafts are placeholders** — default `mock` provider produces
   post-aware but plainly non-final text; voice quality is only measurable
   with `LLM_PROVIDER=groq` or in Session 2.
5. **Evidence file is a seed** — `evidence.md` E1–E7 was written from the
   profile dump, not confirmed line-by-line by him yet.
6. **Single-platform, single-loop by design** — and the loop stops at a mock
   handoff; no path to auto-posting exists in the code.

## Next experiment (after Session 2)

**Re-calibrate triage on his real labels.** With Session 1 labels in place,
sweep `LAYA_CONFIDENCE_THRESHOLD` over {0.40, 0.45, 0.50, 0.55} and pick the
point that maximizes firm agreement with **zero confident-and-wrong** —
using a held-out half of the posts (not all 10) so the eval stays honest.
Decision recorded either way in the decision log (D4 gets an addendum).

Secondary, only if time allows: measure draft edit-distance before/after
accepted rules to test whether `make learn` actually shrinks his rewrite
work — the product's real success signal (`product.md` § Success signal).
