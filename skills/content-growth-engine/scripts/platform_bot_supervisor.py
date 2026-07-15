#!/usr/bin/python3
"""
platform_bot_supervisor.py — keeps platform_bot_listener.py alive.

Runs the listener as a subprocess; restarts on crash with exponential
backoff (2s -> 60s cap). SIGTERM/SIGINT stops cleanly.
"""
import os
import sys
import time
import signal
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PY = r"C:\Python312\python.exe"
LISTENER = os.path.join(HERE, "platform_bot_listener.py")
LOG = os.path.join(HERE, "platform_bot_supervisor.log")

MAX_BACKOFF = 60
FIRST_BACKOFF = 2

def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass

def main():
    child = None
    stopping = False

    def fwd(signum, frame):
        nonlocal stopping
        stopping = True
        log(f"supervisor received {signum}; shutting down")
        if child and child.poll() is None:
            try: child.send_signal(signum)
            except Exception: pass

    signal.signal(signal.SIGTERM, fwd)
    signal.signal(signal.SIGINT, fwd)

    restarts = 0
    backoff = FIRST_BACKOFF
    log("supervisor started — launching listener")
    while not stopping:
        child = subprocess.Popen(
            [PY, LISTENER], cwd=HERE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        log(f"listener launched (pid={child.pid}, restart #{restarts})")
        for chunk in iter(child.stdout.readline, ""):
            sys.stdout.write(chunk); sys.stdout.flush()
            try:
                with open(LOG, "a", encoding="utf-8") as fh: fh.write(chunk)
            except Exception: pass
        rc = child.wait()
        if stopping:
            log(f"child exited (rc={rc}) during shutdown"); break
        log(f"listener exited rc={rc} — restarting in {backoff}s")
        time.sleep(backoff)
        restarts += 1
        backoff = min(backoff * 2, MAX_BACKOFF)
    log("supervisor exited")

if __name__ == "__main__":
    main()
