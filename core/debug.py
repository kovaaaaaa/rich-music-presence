# core/debug.py
import os
import time
from pathlib import Path


_DEBUG = os.getenv("RMP_DEBUG") == "1"


def debug_log(message: str) -> None:
    if not _DEBUG:
        return

    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        ts = "unknown-time"

    line = f"[{ts}] {message}\n"
    try:
        log_path = Path(__file__).resolve().parents[1] / "rmp_debug.log"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

    try:
        print(f"[DEBUG] {message}")
    except Exception:
        pass
