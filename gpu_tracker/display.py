"""Display functions: status table, next command, remaining list."""

import json
import sys
from typing import List, Optional

from .session import Session, Command

# Try rich, fall back to plain text
try:
    from rich.console import Console
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "-"
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}min {s}s" if s else f"{m}min"
    h, m = divmod(m, 60)
    return f"{h}h {m}min"


STATUS_SYMBOLS = {
    "done": "✓",
    "interrupted": "✗",
    "running": "►",
    "pending": "○",
    "skipped": "⊘",
}

STATUS_COLORS = {
    "done": "green",
    "interrupted": "red",
    "running": "yellow",
    "pending": "dim",
    "skipped": "yellow",
}


def print_status(session: Session, as_json: bool = False):
    if as_json:
        print(json.dumps(session.to_dict(), indent=2, ensure_ascii=False))
        return

    counts = session.summary()
    header = f"Session: {session.name} ({session.id})"
    skipped_part = f"  skipped={counts['skipped']}" if counts.get('skipped') else ""
    summary = f"  done={counts['done']}  running={counts['running']}  interrupted={counts['interrupted']}{skipped_part}  pending={counts['pending']}"

    if HAS_RICH:
        console = Console()
        console.print(f"\n[bold]{header}[/bold]")
        console.print(summary)

        table = Table(show_header=True, padding=(0, 1))
        table.add_column("#", justify="right", style="dim", width=3)
        table.add_column("Status", width=6)
        table.add_column("Command")
        table.add_column("Duration", justify="right", width=10)
        table.add_column("Exit", justify="right", width=4)

        for c in session.commands:
            color = STATUS_COLORS.get(c.status, "")
            symbol = STATUS_SYMBOLS.get(c.status, "?")
            exit_str = str(c.exit_code) if c.exit_code is not None else "-"
            table.add_row(
                str(c.id),
                f"[{color}]{symbol} {c.status}[/{color}]",
                c.cmd,
                format_duration(c.duration_seconds),
                exit_str,
            )

        console.print(table)
        console.print()
    else:
        print(f"\n{header}")
        print(summary)
        print(f"{'#':>3}  {'Status':<14}  {'Command':<50}  {'Duration':>10}  {'Exit':>4}")
        print("-" * 90)
        for c in session.commands:
            symbol = STATUS_SYMBOLS.get(c.status, "?")
            exit_str = str(c.exit_code) if c.exit_code is not None else "-"
            status_str = f"{symbol} {c.status}"
            print(f"{c.id:>3}  {status_str:<14}  {c.cmd:<50}  {format_duration(c.duration_seconds):>10}  {exit_str:>4}")
        print()


def print_next(command: Optional[Command]):
    if command is None:
        print("No pending commands.")
        return
    print(f"Next: [{command.id}] {command.cmd}")


def print_remaining(commands: List[Command]):
    if not commands:
        print("No remaining commands.")
        return
    print(f"{len(commands)} remaining:")
    for c in commands:
        symbol = STATUS_SYMBOLS.get(c.status, "?")
        print(f"  {c.id}. {symbol} [{c.status}] {c.cmd}")


def print_sessions(sessions: List[Session]):
    if not sessions:
        print("No sessions found.")
        return
    active_marker = ""
    for s in sessions:
        counts = s.summary()
        total = len(s.commands)
        done = counts["done"]
        print(f"  {s.id}  {s.name:<30}  {done}/{total} done  created={s.created_at}")
