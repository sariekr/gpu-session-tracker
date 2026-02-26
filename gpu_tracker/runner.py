"""Command execution with real-time output capture and periodic session saves."""

import signal
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime

from .session import Session, Command

MAX_LAST_OUTPUT = 20
SAVE_INTERVAL = 5  # seconds


def run_command(command: Command, session: Session) -> Command:
    """Run a command, stream output to terminal, capture last N lines, save periodically."""
    command.status = "running"
    command.started_at = datetime.now().isoformat(timespec="seconds")
    command.last_output = []
    session.save()

    output_buffer = deque(maxlen=MAX_LAST_OUTPUT)
    start_time = time.monotonic()
    interrupted = False

    proc = subprocess.Popen(
        command.cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True,
    )

    # Periodic save in background
    stop_saver = threading.Event()

    def periodic_save():
        while not stop_saver.wait(SAVE_INTERVAL):
            command.last_output = list(output_buffer)
            command.duration_seconds = round(time.monotonic() - start_time, 1)
            try:
                session.save()
            except Exception:
                pass

    saver_thread = threading.Thread(target=periodic_save, daemon=True)
    saver_thread.start()

    # Handle SIGINT/SIGTERM
    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)

    def handle_interrupt(signum, frame):
        nonlocal interrupted
        interrupted = True
        if proc.poll() is None:
            proc.terminate()

    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)

    try:
        for line in proc.stdout:
            line = line.rstrip("\n")
            output_buffer.append(line)
            print(line, flush=True)

        proc.wait()
    except Exception:
        interrupted = True
        if proc.poll() is None:
            proc.terminate()
            proc.wait()
    finally:
        stop_saver.set()
        saver_thread.join(timeout=2)
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)

    elapsed = round(time.monotonic() - start_time, 1)
    command.duration_seconds = elapsed
    command.last_output = list(output_buffer)
    command.exit_code = proc.returncode

    if interrupted or proc.returncode in (-2, -9, -15):
        command.status = "interrupted"
    elif proc.returncode == 0:
        command.status = "done"
        command.finished_at = datetime.now().isoformat(timespec="seconds")
    else:
        command.status = "interrupted"
        command.finished_at = datetime.now().isoformat(timespec="seconds")

    session.save()
    return command
