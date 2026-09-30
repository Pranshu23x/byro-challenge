# Eval report

> Directional, not statistical: ~7 holdout items and ~10 triage items
> from a single founder's real activity. Treat as signal, not measurement.

## Holdout blind test (the riskiest assumption)
- posts evaluated: 7
- posts with >= 1 non-blocked draft: 7
- posts with >= 1 draft passing ALL checks: 7
- founder judgments: **[FILL FROM SESSION 2 — see `session2_results.md`]**

## Triage agreement
- labeled posts: 3 of 10 (unlabeled rows are awaiting Session 1)
- agreement: 100%
- confusion (founder->system): `{"engage->engage": 3, "engage->skip": 0, "skip->engage": 0, "skip->skip": 0}`

### Confident and wrong (system confidence >= 0.70 but disagreed)
- none in this run

### Per-post rows
```json
[
  {
    "id": "t01",
    "system": "engage",
    "backend": "laya",
    "confidence": 0.72,
    "founder_label": "engage",
    "founder_reason": "DERIVED (he commented 'W' on this post; confirm in Session 1)"
  },
  {
    "id": "t02",
    "system": "engage",
    "backend": "laya",
    "confidence": 0.54,
    "founder_label": "engage",
    "founder_reason": "DERIVED (he commented '\ud83d\ude80' on this post; confirm in Session 1)"
  },
  {
    "id": "t03",
    "system": "founder_decides",
    "backend": "laya",
    "confidence": 0.45,
    "founder_label": "engage",
    "founder_reason": "DERIVED (he commented 'i just use Byro'; confirm in Session 1)"
  },
  {
    "id": "t04",
    "system": "founder_decides",
    "backend": "laya",
    "confidence": 0.48,
    "founder_label": "engage",
    "founder_reason": "DERIVED (he commented 'he is pretty cool ngl'; confirm in Session 1)"
  },
  {
    "id": "t05",
    "system": "founder_decides",
    "backend": "laya",
    "confidence": 0.38,
    "founder_label": "engage",
    "founder_reason": "DERIVED (he commented 'f reddit ngl'; confirm in Session 1)"
  },
  {
    "id": "t06",
    "system": "founder_decides",
    "backend": "laya",
    "confidence": 0.45,
    "founder_label": "engage",
    "founder_reason": "DERIVED (he commented 'do what you love and the money comes to you!'; confirm in Session 1)"
  },
  {
    "id": "t07",
    "system": "founder_decides",
    "backend": "laya",
    "confidence": 0.47,
    "founder_label": "engage",
    "founder_reason": "DERIVED (he commented 'facts'; confirm in Session 1)"
  },
  {
    "id": "t08",
    "system": "founder_decides",
    "backend": "laya",
    "confidence": 0.48,
    "founder_label": null,
    "founder_reason": "He reacted to this post but did not comment. Label unknown; fill in Session 1."
  },
  {
    "id": "t09",
    "system": "engage",
    "backend": "laya",
    "confidence": 0.59,
    "founder_label": "engage",
    "founder_reason": "DERIVED (he commented '\ud83c\udde5\ud83d\ude80'; confirm in Session 1)"
  },
  {
    "id": "t10",
    "system": "founder_decides",
    "backend": "laya",
    "confidence": 0.42,
    "founder_label": "engage",
    "founder_reason": "DERIVED (he commented 'congrats!'; confirm in Session 1)"
  }
]
```
