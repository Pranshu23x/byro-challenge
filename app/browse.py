"""Interactive case browser: a demoable picker over 3 ranked comments.

Flow per case (responses are never pre-shown):

    1. the post alone + a [ Get Response ] prompt
    2. Enter  -> a short loading animation (feels live, not canned)
    3. the 3 candidates appear ranked (★ first), and:

       ↑ / ↓   move the highlight        Enter   copy to clipboard + log approve
       → / n   next case                 ← / b   previous case
       s       skip + log skip           q       quit

    4. selecting shows a clear "Copied to clipboard" confirmation block.

Selecting = "this response is what I want": the comment lands in the system
clipboard AND is logged as an approved decision in the append-only stores.
The human still pastes it into LinkedIn himself — nothing here can post.

UI carries no internal jargon (no backend/model names); a small footer says
the sample posts are canned demo data. Zero dependencies: msvcrt/termios for
keys, Win32 clipboard API (app/clipboard.py). Every side effect — including
the loading sleep — is injectable so the flow is testable offline.
"""
import os
import sys
import textwrap
import time

from app.clipboard import copy_text
from app.judge import order_drafts
from app.review import approve, read_proposals, record_decision

RULE = "-" * 66
FOOTER = "demo \u00b7 sample posts \u00b7 canned data"
SPINNER = "\u280b\u2819\u2839\u2838\u283c\u2834\u2826\u2807"
LOADING_TICKS = 8
LOADING_STEP = 0.12

KEYS_PROMPT = ("  [ Get Response ]        n next \u00b7 b back \u00b7 "
               "s skip \u00b7 q quit")
KEYS_PICK = ("  \u2191\u2193 choose \u00b7 Enter = copy \u00b7 n next \u00b7 "
             "b back \u00b7 s skip \u00b7 q quit")

BROWSE_STATUSES = ("drafted", "blocked", "founder_decides")


def _is_blocked(d: dict) -> bool:
    return any(f.get("severity") == "block" for f in d.get("flags") or [])


def ranked_drafts(prop: dict) -> list[dict]:
    """The 3 candidates in preference order (blocked last)."""
    return order_drafts(prop.get("drafts") or [], prop.get("recommended"),
                        prop.get("scores") or {})


def _header(index: int, total: int) -> str:
    left = "  Byro \u00b7 adaptive commenting"
    right = f"Case {index + 1} of {total}"
    return left + " " * max(1, 66 - len(left) - len(right)) + right


def _one_line(text: str, limit: int) -> str:
    flat = " ".join((text or "").split())
    return flat if len(flat) <= limit else flat[:limit].rstrip() + "..."


def _notice_block(notice: str | None) -> list[str]:
    if not notice:
        return []
    return ["  " + notice, ""]


def format_prompt(prop: dict, index: int, total: int,
                  notice: str | None = None) -> str:
    """Phase 1: just the post and a Get Response button — no drafts."""
    lines = [RULE, _header(index, total), RULE, "", "  POST", ""]
    lines += ["  " + w for w in
              (textwrap.wrap(_one_line(prop.get("post_text") or "", 200), 62)
               or ["(empty post)"])]
    lines += ["", RULE, ""]
    lines += _notice_block(notice)
    if not ranked_drafts(prop):
        lines += ["  (no responses available for this case)", ""]
    lines += [KEYS_PROMPT, "", RULE, "  " + FOOTER]
    return "\n".join(lines)


def format_loading(prop: dict, index: int, total: int, tick: int = 0) -> str:
    """Phase 2: same frame, spinner where the button was."""
    frame = format_prompt(prop, index, total)
    spinner = SPINNER[tick % len(SPINNER)]
    return frame.replace(KEYS_PROMPT,
                         f"  {spinner}  getting a response...")


def format_responses(prop: dict, sel: int, index: int, total: int,
                     notice: str | None = None) -> str:
    """Phase 3: the 3 candidates, ranked, selector on the highlight."""
    lines = [RULE, _header(index, total), RULE, "",
             "  Re: " + _one_line(prop.get("post_text") or "", 58), ""]
    ranked = ranked_drafts(prop)
    scores = prop.get("scores") or {}
    if not ranked:
        lines += ["  (no responses)", ""]
    for i, d in enumerate(ranked):
        mark = "\u25ba " if i == sel else "  "
        star = " \u2605" if d.get("id") == prop.get("recommended") else ""
        sc = scores.get(d.get("id"))
        sc_s = f"  \u00b7  {sc:.2f}" if isinstance(sc, (int, float)) else ""
        blocked_s = "  [BLOCKED]" if _is_blocked(d) else ""
        lines.append(f"{mark}{i + 1}{star} {d.get('angle', '?')}{sc_s}"
                     f"{blocked_s}")
        words = textwrap.wrap(d.get("text", "") or "", 56) or [""]
        for j, w in enumerate(words):
            quote = "'" if j == 0 else ""
            end = "'" if j == len(words) - 1 else ""
            lines.append(f"      {quote}{w}{end}")
        lines.append("")
    lines += _notice_block(notice)
    lines += [RULE, KEYS_PICK, RULE, "  " + FOOTER]
    return "\n".join(lines)


def format_case(prop: dict, sel: int, index: int, total: int) -> str:
    """Both frames joined — used for the non-tty static listing only."""
    body = format_responses(prop, sel, index, total).splitlines()[3:]
    return format_prompt(prop, index, total) + "\n" + "\n".join(body)


def format_copied(ok: bool, draft_text: str) -> str:
    """The confirmation block shown after Enter on a response."""
    lines = ["", RULE]
    if ok:
        lines.append("  \u2713  Copied to clipboard \u2014 paste it into "
                     "LinkedIn yourself")
    else:
        lines.append("  !  Clipboard unavailable \u2014 copy this manually:")
        lines += ["      " + w for w in
                  textwrap.wrap(draft_text or "", 58)]
    lines.append("  approved & logged \u00b7 [any key \u2192 next case]")
    lines.append(RULE)
    return "\n".join(lines)


def format_skipped() -> str:
    return "\n".join(["", RULE, "  \u2717  Skipped (logged) \u00b7 "
                      "[any key \u2192 next case]", RULE])


def read_key() -> str:
    """One keypress, normalized: up/down/left/right/enter/quit/letter/''."""
    if sys.platform == "win32":
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):  # Windows extended keys (arrows)
            ch2 = msvcrt.getwch()
            return {"H": "up", "P": "down", "K": "left",
                    "M": "right"}.get(ch2, "")
        if ch in ("\r", "\n"):
            return "enter"
        if ch == "\x03":  # Ctrl+C
            return "quit"
        return ch.lower()
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            seq = sys.stdin.read(2)
            return {"[A": "up", "[B": "down", "[C": "right",
                    "[D": "left"}.get(seq, "")
        if ch in ("\r", "\n"):
            return "enter"
        if ch == "\x03":
            return "quit"
        return ch.lower()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def run_browse(proposals: list[dict], *, read_key, copy_fn, approve_fn=None,
               skip_fn=None, write=print, clear=None,
               sleep=time.sleep) -> dict:
    """Engine over `proposals`; every side effect is injectable (tests)."""
    if approve_fn is None:
        approve_fn = lambda prop, draft: approve(prop, draft,
                                                 reason="selected in browse")
    if skip_fn is None:
        skip_fn = lambda prop: record_decision("skip",
                                               prop.get("post_id", ""), "")
    stats = {"selected": 0, "skipped": 0, "quit": False}
    total = len(proposals)
    i = 0

    def redraw(frame: str) -> None:
        if clear:
            clear()
        write(frame)

    def pause(msg: str) -> bool:
        """Show a confirmation and hold the screen until any key.
        False = user pressed q during the pause."""
        write(msg)
        if read_key() in ("q", "quit"):
            stats["quit"] = True
            write("\nbye.")
            return False
        return True

    while 0 <= i < total:
        prop = proposals[i]
        ranked = ranked_drafts(prop)
        sel = 0
        phase = "ask"
        notice = None
        advance = None
        while True:
            if phase == "ask":
                redraw(format_prompt(prop, i, total, notice))
            else:
                redraw(format_responses(prop, sel, i, total, notice))
            key = read_key()
            notice = None
            if key in ("q", "quit"):
                stats["quit"] = True
                write("\nbye.")
                return stats
            if key in ("right", "n"):
                advance = 1
                break
            if key in ("left", "b"):
                if i > 0:
                    advance = -1
                    break
                notice = "(already at the first case)"
                continue
            if key == "s":
                skip_fn(prop)
                stats["skipped"] += 1
                if not pause(format_skipped()):
                    return stats
                advance = 1
                break
            if phase == "ask":
                if key == "enter":
                    if not ranked:
                        notice = "(no responses available for this case)"
                        continue
                    redraw(format_loading(prop, i, total, 0))
                    for t in range(1, LOADING_TICKS):
                        sleep(LOADING_STEP)
                        redraw(format_loading(prop, i, total, t))
                    sleep(LOADING_STEP)
                    phase = "show"
                continue
            # phase == "show"
            if key == "up" and ranked:
                sel = (sel - 1) % len(ranked)
            elif key == "down" and ranked:
                sel = (sel + 1) % len(ranked)
            elif key == "enter":
                if not ranked:
                    notice = "(no responses available for this case)"
                    continue
                draft = ranked[sel]
                if _is_blocked(draft):
                    notice = ("blocked drafts cannot be selected "
                              "(prohibited claim) \u2014 pick another")
                    continue
                try:
                    approve_fn(prop, draft)
                except PermissionError as e:
                    notice = str(e)
                    continue
                ok = copy_fn(draft.get("text", ""))
                stats["selected"] += 1
                if not pause(format_copied(ok, draft.get("text", ""))):
                    return stats
                advance = 1
                break
        i += advance or 0
    write(f"\nDone: {stats['selected']} selected (copied + approved), "
          f"{stats['skipped']} skipped, {total} case(s).")
    return stats


def browse_cli(path=None, interactive: bool | None = None) -> int:
    proposals = [p for p in read_proposals(path)
                 if p.get("status") in BROWSE_STATUSES and p.get("drafts")]
    if not proposals:
        print("nothing to browse (run `make run` first).")
        return 0
    if interactive is None:
        interactive = sys.stdin.isatty()
    if not interactive:
        print(f"{len(proposals)} case(s) — run in a real terminal for the "
              f"interactive picker; static listing below.")
        for i, prop in enumerate(proposals):
            print()
            print(format_case(prop, 0, i, len(proposals)))
        return 0
    try:
        run_browse(proposals, read_key=read_key, copy_fn=copy_text,
                   clear=_clear)
    except KeyboardInterrupt:
        print("\nbye.")
    return 0
