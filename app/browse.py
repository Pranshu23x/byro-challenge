"""Interactive case browser: arrow keys pick among 3 ranked comments.

Flow per case: the 3 candidates are shown ranked by Laya's style-fit score
(★ first), highlight starts on Laya's pick, and:

    ↑ / ↓   move the highlight        Enter   copy to clipboard + log approve
    → / n   next case                 ← / b   previous case
    s       skip + log skip           q       quit

Selecting = "this response is what I want": the comment lands in the system
clipboard AND is logged as an approved decision in the append-only stores.
The human still pastes it into LinkedIn himself — nothing here can post.

Zero dependencies: msvcrt on Windows / termios elsewhere for keys; Win32
clipboard API (see app/clipboard.py). Engine functions take injectable
read_key/copy/approve functions so the whole flow is testable offline.
"""
import os
import sys

from app.clipboard import copy_text
from app.judge import order_drafts
from app.review import approve, read_proposals, record_decision

KEYS_HELP = ("  \u2191/\u2193 choose \u00b7 Enter = copy + approve \u00b7 "
             "\u2192/n next \u00b7 \u2190/b back \u00b7 s skip + log \u00b7 q quit")

BROWSE_STATUSES = ("drafted", "blocked", "founder_decides")


def _is_blocked(d: dict) -> bool:
    return any(f.get("severity") == "block" for f in d.get("flags") or [])


def ranked_drafts(prop: dict) -> list[dict]:
    """The 3 candidates in Laya-preference order (blocked last)."""
    return order_drafts(prop.get("drafts") or [], prop.get("recommended"),
                        prop.get("scores") or {})


def format_case(prop: dict, sel: int, index: int, total: int) -> str:
    """Pure renderer for one case (also used for the non-tty fallback)."""
    tri = prop.get("triage") or {}
    lines = ["-" * 66,
             f"Case {index + 1}/{total} \u00b7 {prop.get('post_id')} \u00b7 "
             f"status={prop.get('status')} \u00b7 "
             f"triage={tri.get('decision')} ({tri.get('backend')})"]
    if tri.get("reason"):
        lines.append(f"  why: {tri['reason']}")
    if prop.get("judge"):
        lines.append(f"  judge: {prop['judge']}")
    text = " ".join((prop.get("post_text") or "").split())
    if len(text) > 320:
        text = text[:320] + "..."
    lines.append(f"  post: {text}")
    lines.append("")
    ranked = ranked_drafts(prop)
    scores = prop.get("scores") or {}
    if not ranked:
        lines.append("  (no drafts)")
    for i, d in enumerate(ranked):
        mark = "\u25ba " if i == sel else "  "
        star = " \u2605" if d.get("id") == prop.get("recommended") else ""
        sc = scores.get(d.get("id"))
        sc_s = f" \u00b7 score {sc:.2f}" if isinstance(sc, (int, float)) else ""
        blocked_s = " [BLOCKED]" if _is_blocked(d) else ""
        lines.append(f"{mark}[{i + 1}]{star} {d.get('angle', '?')}{sc_s}{blocked_s}")
        lines.append(f"      {d.get('text', '')!r}")
    lines.append("")
    lines.append(KEYS_HELP)
    return "\n".join(lines)


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
               skip_fn=None, write=print, clear=None) -> dict:
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
        advance = None
        while True:
            if clear:
                clear()
            write(format_case(prop, sel, i, total))
            key = read_key()
            if key in ("q", "quit"):
                stats["quit"] = True
                write("\nbye.")
                return stats
            if key == "up" and ranked:
                sel = (sel - 1) % len(ranked)
            elif key == "down" and ranked:
                sel = (sel + 1) % len(ranked)
            elif key == "enter":
                if not ranked:
                    write("  nothing to select here.")
                    continue
                draft = ranked[sel]
                if _is_blocked(draft):
                    write("  blocked drafts cannot be selected "
                          "(prohibited claim) — pick another.")
                    continue
                try:
                    approve_fn(prop, draft)
                except PermissionError as e:
                    write(f"  {e}")
                    continue
                ok = copy_fn(draft.get("text", ""))
                if ok:
                    msg = ("  \u2713 copied to clipboard + logged as approved "
                           "\u2014 paste it into LinkedIn yourself.  "
                           "[any key \u2192 next case]")
                else:
                    msg = ("  logged as approved, but clipboard failed — "
                           "copy manually:  " + repr(draft.get("text", "")) +
                           "   [any key \u2192 next case]")
                stats["selected"] += 1
                if not pause(msg):
                    return stats
                advance = 1
                break
            elif key in ("right", "n"):
                advance = 1
                break
            elif key in ("left", "b"):
                if i > 0:
                    advance = -1
                    break
                write("  (already at the first case)")
            elif key == "s":
                skip_fn(prop)
                stats["skipped"] += 1
                if not pause("  skipped (logged).  [any key \u2192 next case]"):
                    return stats
                advance = 1
                break
            # any other key: re-render
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
              f"arrow-key picker; static listing below.")
        for i, prop in enumerate(proposals):
            print()
            print(format_case(prop, 0, i, len(proposals)))
        return 0
    print("Browse — 3 comments per case, ranked by Laya's preference "
          "(\u2605 = Laya's pick). Press keys as shown.\n")
    try:
        run_browse(proposals, read_key=read_key, copy_fn=copy_text,
                   clear=_clear)
    except KeyboardInterrupt:
        print("\nbye.")
    return 0
