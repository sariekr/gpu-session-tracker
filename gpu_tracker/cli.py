"""CLI entry point for gpu-tracker."""

import argparse
import sys

from . import __version__
from .session import (
    create_session,
    load_active_session,
    list_sessions,
    delete_session,
)
from .runner import run_command
from .display import (
    print_status,
    print_next,
    print_remaining,
    print_sessions,
)


def require_session():
    session = load_active_session()
    if session is None:
        print("No active session. Run 'gpu-tracker init <name>' first.", file=sys.stderr)
        sys.exit(1)
    return session


def cmd_init(args):
    session = create_session(args.name)
    print(f"Session created: {session.id} ({session.name})")


def cmd_add(args):
    session = require_session()
    command = session.add_command(args.command)
    print(f"Added [{command.id}]: {command.cmd}")


def cmd_run(args):
    session = require_session()
    command = session.add_command(args.command)
    print(f"Running [{command.id}]: {command.cmd}")
    print("-" * 60)
    run_command(command, session)
    print("-" * 60)
    symbol = "✓" if command.status == "done" else "✗"
    print(f"{symbol} [{command.id}] {command.status} (exit={command.exit_code})")


def cmd_next(args):
    session = require_session()
    command = session.get_next()
    if not args.run:
        print_next(command)
        return
    if command is None:
        print("No pending commands.")
        return
    print(f"Running [{command.id}]: {command.cmd}")
    print("-" * 60)
    run_command(command, session)
    print("-" * 60)
    symbol = "✓" if command.status == "done" else "✗"
    print(f"{symbol} [{command.id}] {command.status} (exit={command.exit_code})")


def cmd_status(args):
    session = require_session()
    print_status(session, as_json=args.json)


def cmd_remaining(args):
    session = require_session()
    print_remaining(session.get_remaining())


def cmd_skip(args):
    session = require_session()
    skipped = session.skip_interrupted()
    if not skipped:
        print("No interrupted commands to skip.")
        return
    for c in skipped:
        print(f"Skipped [{c.id}]: {c.cmd}")


def cmd_run_all(args):
    session = require_session()
    ran = 0
    skipped = 0
    failed = 0
    while True:
        command = session.get_next()
        if command is None:
            break
        ran += 1
        print(f"Running [{command.id}]: {command.cmd}")
        print("-" * 60)
        run_command(command, session)
        print("-" * 60)
        if command.status == "done":
            print(f"✓ [{command.id}] done (exit={command.exit_code})")
        else:
            if args.skip_errors:
                command.status = "skipped"
                session.save()
                print(f"⊘ [{command.id}] skipped (exit={command.exit_code})")
                skipped += 1
            else:
                print(f"✗ [{command.id}] {command.status} (exit={command.exit_code})")
                print("Stopped. Use --skip-errors to continue past failures.")
                failed += 1
                break
    if ran == 0:
        print("No pending commands.")
    else:
        print(f"\nFinished: {ran} ran, {skipped} skipped, {failed} failed")


def cmd_retry(args):
    session = require_session()
    command = session.get_interrupted()
    if command is None:
        print("No interrupted commands.")
        return
    command.status = "pending"
    command.exit_code = None
    command.started_at = None
    command.finished_at = None
    command.duration_seconds = None
    command.last_output = []
    session.save()
    print(f"Retrying [{command.id}]: {command.cmd}")
    print("-" * 60)
    run_command(command, session)
    print("-" * 60)
    symbol = "✓" if command.status == "done" else "✗"
    print(f"{symbol} [{command.id}] {command.status} (exit={command.exit_code})")


def cmd_list(args):
    sessions = list_sessions()
    print_sessions(sessions)


def cmd_delete(args):
    if delete_session(args.session_id):
        print(f"Deleted session: {args.session_id}")
    else:
        print(f"Session not found: {args.session_id}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="gpu-tracker",
        description="GPU Session Recovery Tool — track commands, recover from crashes",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Create a new session")
    p_init.add_argument("name", help="Session name")
    p_init.set_defaults(func=cmd_init)

    # add
    p_add = sub.add_parser("add", help="Add a command to the session")
    p_add.add_argument("command", help="Command to add")
    p_add.set_defaults(func=cmd_add)

    # run
    p_run = sub.add_parser("run", help="Add and immediately run a command")
    p_run.add_argument("command", help="Command to run")
    p_run.set_defaults(func=cmd_run)

    # next
    p_next = sub.add_parser("next", help="Show or run the next pending command")
    p_next.add_argument("--run", action="store_true", help="Run it instead of just showing")
    p_next.set_defaults(func=cmd_next)

    # status
    p_status = sub.add_parser("status", help="Show session status")
    p_status.add_argument("--json", action="store_true", help="Output as JSON")
    p_status.set_defaults(func=cmd_status)

    # remaining
    p_remaining = sub.add_parser("remaining", help="List remaining commands")
    p_remaining.set_defaults(func=cmd_remaining)

    # run-all
    p_run_all = sub.add_parser("run-all", help="Run all pending commands sequentially")
    p_run_all.add_argument("--skip-errors", action="store_true", help="Skip failed commands and continue")
    p_run_all.set_defaults(func=cmd_run_all)

    # skip
    p_skip = sub.add_parser("skip", help="Mark all interrupted commands as skipped")
    p_skip.set_defaults(func=cmd_skip)

    # retry
    p_retry = sub.add_parser("retry", help="Retry the first interrupted command")
    p_retry.set_defaults(func=cmd_retry)

    # list
    p_list = sub.add_parser("list", help="List all sessions")
    p_list.set_defaults(func=cmd_list)

    # delete
    p_delete = sub.add_parser("delete", help="Delete a session")
    p_delete.add_argument("session_id", help="Session ID to delete")
    p_delete.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
