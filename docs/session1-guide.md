# Session 1 guide — ground truth with the founder (~45–60 min)

Goal: replace every DERIVED/provisional marker with his word, so the system's
labels and boundaries are *his*, not mine.

## Prep (2 min)

```bash
make test    # must be green before showing anything
make run     # current proposals, Laya triage live if service is up
```

Have open: `reports/eval_report.md` (per-post table), `data/triage_posts.jsonl`,
`data/founder/interests.json`, `data/founder/evidence.md`,
`data/founder/prohibited.md`, `data/SOURCES.md`.

## Agenda

1. **Consent & provenance (5 min)** — confirm his public comments may be used
   as fixtures for this exercise. Fill the `[FILL FROM SESSION NOTES]` in
   `data/SOURCES.md`. If he declines anything, delete that row immediately.
2. **Triage labels (20 min)** — walk the 10 posts in `eval_report.md`
   § Per-post rows. For each: was he *likely to engage* (`engage`) or *skip*?
   He also sees the system's call + confidence — first agreement numbers come
   from his **own** label before he sees ours (avoid anchoring: label first,
   reveal after). Write `founder_label` + one-line `founder_reason` into
   `data/triage_posts.jsonl`; t08 (reacted, no comment) needs a real answer.
3. **Interest map (10 min)** — confirm the 13 topics + weights; he adds/drops
   topics. This file *is* the Laya engage criteria (D4), so this is the
   highest-leverage ten minutes of the session.
4. **Boundaries (10 min)** — review `evidence.md` (claims he may assert) and
   `prohibited.md` (hard blocks). Anything conservative-but-wrong he can
   loosen; anything dangerous he should tighten. Fill evidence consent note.
5. **Voice spot-check (5 min)** — read 3 mock-mode drafts (`make run` output
   or `runs/proposals.jsonl`) and say what feels off; capture verbatim only
   what *he* says (no paraphrasing into the log).

## Done means

- [ ] no `[FILL …]` left in `SOURCES.md` consent block (or an explicit "no")
- [ ] all 10 triage rows labeled by him, `t08` resolved
- [ ] `interests.json` reweighted if he disagreed
- [ ] `evidence.md` / `prohibited.md` confirmed or edited
- [ ] `make eval` rerun → agreement + confident-and-wrong recomputed with his
      labels (revisit `LAYA_CONFIDENCE_THRESHOLD` only if a firm call was
      wrong — record the change in the decision log)
- [ ] his exact quotes (if any) pasted into `feedback-and-next.md`

## Rules for me during the session

- Never write what he "probably" meant — ask, or leave `[FILL]`.
- Show the blind packet (`reports/review_packet.md`) only in Session 2.
- No new features during the session; note requests in
  `feedback-and-next.md` instead.
