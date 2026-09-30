"""Copy text to the system clipboard with zero third-party dependencies.

Windows: Win32 clipboard API via ctypes (no subprocess, no quoting issues).
macOS/Linux: pbcopy / wl-copy / xclip when present. Any failure returns
False — the caller shows the text so it can be copied by hand.
"""
import shutil
import subprocess
import sys


def copy_text(text: str) -> bool:
    if not text:
        return False
    if sys.platform == "win32":
        return _windows_copy(text)
    for cmd in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=text.encode("utf-8"), check=True,
                               timeout=5)
                return True
            except Exception:
                continue
    return False


def _windows_copy(text: str) -> bool:
    import ctypes

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    u32 = ctypes.windll.user32
    k32 = ctypes.windll.kernel32
    # Explicit 64-bit-safe prototypes: without these, ctypes defaults every
    # handle to c_int and truncates it on x64 (found by live testing).
    u32.OpenClipboard.argtypes = [ctypes.c_void_p]
    u32.OpenClipboard.restype = ctypes.c_bool
    u32.EmptyClipboard.restype = ctypes.c_bool
    u32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    u32.SetClipboardData.restype = ctypes.c_void_p
    u32.CloseClipboard.restype = ctypes.c_bool
    k32.GlobalAlloc.argtypes = [ctypes.c_size_t, ctypes.c_size_t]
    k32.GlobalAlloc.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [ctypes.c_void_p]
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    k32.GlobalFree.argtypes = [ctypes.c_void_p]
    if not u32.OpenClipboard(None):
        return False
    handle = None
    try:
        if not u32.EmptyClipboard():
            return False
        buf = ctypes.create_unicode_buffer(text)
        size = ctypes.sizeof(buf)
        handle = k32.GlobalAlloc(GMEM_MOVEABLE, size)
        if not handle:
            return False
        ptr = k32.GlobalLock(handle)
        if not ptr:
            return False
        ctypes.memmove(ptr, buf, size)
        k32.GlobalUnlock(handle)
        if not u32.SetClipboardData(CF_UNICODETEXT, handle):
            return False
        handle = None  # clipboard now owns the allocation
        return True
    except Exception:
        return False
    finally:
        if handle:
            k32.GlobalFree(handle)
        u32.CloseClipboard()
