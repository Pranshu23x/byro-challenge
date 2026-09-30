# Product definition — adaptive LinkedIn commenting

## Challenging the premise (with user evidence)

The challenge frames the need as *contributing consistently*. The founder's
own activity argues otherwise: he already comments heavily (18 real pairs in
the dump) and skips plenty of posts on purpose ("f reddit ngl" was a reply to
a growth-bait post). His actual pain isn't habit or volume — it's **picking
the right moment** and **not sounding like AI when he does reply**. So the
product leads with triage (when to stay silent is half the value) and treats
drafts as candidates he may reject, not as throughput.

## Riskiest assumption — what architecture alone cannot prove

> **That a system-drafted comment will read as *him*.** Tests can prove the
> screens fire, the holdout never leaks, rules version and roll back — none of
> that proves Rico will accept a draft without rewriting it, or that he
> can't tell it from his own comment. Voice acceptance is the whole bet; it
> is only provable by him, blind.

## The thin executable proof (task 5)

`make eval` renders `reports/review_packet.md`: 7 holdout posts the system
**never saw as examples**, each showing candidate drafts *plus one of his real
comments* — so he must both pick what he'd send and identify which is his.
The answer key (`answer_key.json`) stays sealed until he answers. If he sends
a system draft as-is, or mistakes one for his own, the riskiest assumption
survives its first test; if he doesn't, we learned it cheaply in minutes
instead of after shipping. Full protocol: [`session2_results.md`](../reports/session2_results.md).

## The user and his evidence

Rico Soots, 19, founder of Byro (AI head of content for B2B teams), Tallinn.
He already engages heavily on LinkedIn — but *as himself, quickly, and only
when a post is actually in his world*. Evidence used (provenance in
[`data/SOURCES.md`](../data/SOURCES.md)):

- **18 real comment pairs** (`data/voice_examples.jsonl`) — his comments on
  others' posts. Voice: 1–6 words, lowercase, playful, never "Great post!".
- **His own posts** (`data/founder/own_posts.jsonl`) — what he talks about and
  how he phrases offers ("dm me").
- **Public profile + activity** (`data/founder/profile.md`) — positioning,
  topics, writing style.
- **Derived interest map** (`data/founder/interests.json`) — 13 topics weighted
  by what he demonstrably replies to (funding news, hackathons, dev tools,
  hiring, marketing, building in public…), each with the evidence string.

Why he engages: visibility for Byro, being useful to founder peers, hiring,
and genuine interest in the Estonian/startup scene. What makes a comment
valuable *to him*: short, specific, adding a real angle — not applause.

## The one narrow loop

```
post in  ->  should he engage?  ->  1-3 draft comments in his voice
          (triage)                     (grounded in his claims + examples)
        ->  HE approves / edits / rejects  ->  he posts it himself (handoff)
        ->  his edits teach accepted voice rules  ->  better next drafts
```

One post at a time, batch of 10 per run. Nothing else.

## Success signal (what we measure)

1. **Triage agreement** — system's firm engage/skip calls match the founder's
   labels; *confident-and-wrong* (confidence ≥ threshold, disagree) must be 0
   (`reports/eval_report.md`).
2. **Blind holdout judgments** — on 7 posts he has never seen labeled, does he
   judge each draft usable (A/B/C/D packet, answer key sealed until he
   answers)?
3. **Edit distance shrinking** — over sessions, fewer rewrites before
   approval; his edits become rule-sized (`make learn`), accepted rules are
   versioned and inspectable.

## When the system must do nothing

| Condition | Behavior |
|---|---|
| injection / sensitive post | skipped *before* any model sees it |
| Laya confidence < threshold (0.50) or LLM < 0.70 | `founder_decides` — drafts still attached, never auto-picked |
| model error / unparseable JSON | status `error`, **zero drafts** (no guessed text) |
| every draft hits a prohibited-claim block | status `blocked`; blocked drafts cannot be approved |
| no accepted rules / no evidence | drafts still offered, but flagged checks stay conservative |

## Non-goals (explicitly out of scope)

- Auto-posting, scheduling, LinkedIn login/scraping/browsing of any kind
- Multi-user, teams, multi-platform (X, Bluesky…), analytics dashboards
- Comment *ranking* or an "always engage" autopilot — human decides each time
- Inventing facts, headlines, or engagement bait — claims must come from the
  post or `evidence.md`
- Production infra: auth, billing, deployment (per brief)

## Where automation becomes uncomfortable (and how we stop there)

He is comfortable with: triage suggestions, draft candidates, rule proposals.
He is *not* comfortable with: anything posted under his name without him
seeing it, comments on sensitive topics, or the system pretending certainty.
Hence: mock handoff (he pastes into LinkedIn himself), deterministic skips for
sensitive content, and the `founder_decides` status whenever confidence is
thin. Every accepted rule is one keystroke away from rollback
(`python -m app rules rollback N`).
