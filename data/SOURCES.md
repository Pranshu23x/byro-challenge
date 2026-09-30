# SOURCES — provenance, consent, anonymisation

**Collection date:** 2026-09-30
**Collected by:** the candidate's design partner (Pranshu Kumar) from the
founder's **public LinkedIn activity pages** (profile page and "All activity"
tab), viewed logged-out-style in a normal browser session. **No scraping tool,
no LinkedIn API, no automation, no login credentials used by the pipeline.**
The pages were read by hand and pasted into this repository.

**Consent:** [FILL FROM SESSION NOTES — confirm the founder agreed his public
comments/ posts may be used as training/eval fixtures for this exercise.
Consent assumed granted by the challenge setup ("supplied fixtures,
synthetic or consented post fixtures"); must be re-confirmed in Session 1.]

**What is in the repo:**

| File | Rows | Source |
|---|---|---|
| `data/voice_examples.jsonl` | 18 | founder's real comments on *other people's* posts, read off his public activity page |
| `data/holdout.jsonl` | 7 | same source; **set aside before any development, never shown to the model** |
| `data/triage_posts.jsonl` | 10 | posts he commented on (label `engage` **derived from the observed comment**, marked `DERIVED`) + 1 reacted-only post left `null` for Session 1 |
| `data/founder/own_posts.jsonl` | 6 | his own posts from the profile export + activity page |
| `data/founder/profile.md` | 1 | his public headline and observable writing style |
| `data/founder/interests.json` | 13 topics | derived from which posts he actually engaged with |
| `data/founder/evidence.md` | 7 | claims cited from his own public posts only |
| `data/founder/prohibited.md` | 6 | **conservative defaults, not founder statements** — Session 1 |

**Anonymisation:**
- Third-party **person names inside post text** are replaced with `[NAME]` or
  replaced with generic references where the sentence allows.
- Comments that start with a LinkedIn reply-prefix (`"FirstName: ..."`) had the
  prefix stripped; the founder's own words are unchanged.
- Post text of two very long posts is abridged with `…`-free trimming (only
  trailing boilerplate/hashtag blocks removed; no wording altered inside
  retained text).
- Company/product names (bilt.me, Zero, YC…) were **left in** because they are
  part of what makes the post recognisable to the founder during the blind
  test; they are public company info, not personal data. Flag in Session 1 if
  this is too loose.
- **No third-party profile URLs, avatar URLs or LinkedIn IDs** of other people
  are stored in this repo.

**Known data gaps (honest list):**
1. Only 7 holdout pairs exist (plan wanted ~10) — short, high-volume comment
   style leaves fewer substantive pairs.
2. No founder-labelled **skip** examples yet — every observed engagement was a
   comment or reaction. Session 1 must supply ~5 posts he'd skip.
3. `triage_posts` engage labels are *derived from behaviour*, not yet founder-
   confirmed; marked `DERIVED` in the reason field.
4. `evidence.md` / `prohibited.md` are seeds, not session outputs.

**Excluded by design:** anything not publicly visible; messages; connection
invites; third-party comment threads he did not participate in.
