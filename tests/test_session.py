"""Tests for gpu-tracker session and runner."""

import json
import os
import tempfile
import time

import pytest

from gpu_tracker.session import (
    Session,
    Command,
    create_session,
    load_active_session,
    list_sessions,
    delete_session,
    TRACKER_DIR,
)
from gpu_tracker.runner import run_command


@pytest.fixture
def tmp_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestCommand:
    def test_defaults(self):
        c = Command(id=1, cmd="echo hi")
        assert c.status == "pending"
        assert c.exit_code is None
        assert c.last_output == []

    def test_roundtrip(self):
        c = Command(id=1, cmd="echo hi", status="done", exit_code=0)
        d = c.to_dict()
        c2 = Command.from_dict(d)
        assert c2.cmd == c.cmd
        assert c2.status == c.status


class TestSession:
    def test_create_and_load(self, tmp_cwd):
        session = create_session("test session", cwd=str(tmp_cwd))
        assert session.name == "test session"
        assert (tmp_cwd / TRACKER_DIR).exists()

        loaded = load_active_session(cwd=str(tmp_cwd))
        assert loaded is not None
        assert loaded.id == session.id
        assert loaded.name == session.name

    def test_add_command(self, tmp_cwd):
        session = create_session("test", cwd=str(tmp_cwd))
        c1 = session.add_command("echo hello")
        c2 = session.add_command("echo world")
        assert c1.id == 1
        assert c2.id == 2
        assert len(session.commands) == 2

    def test_get_next(self, tmp_cwd):
        session = create_session("test", cwd=str(tmp_cwd))
        session.add_command("echo 1")
        session.add_command("echo 2")
        nxt = session.get_next()
        assert nxt.id == 1
        nxt.status = "done"
        nxt = session.get_next()
        assert nxt.id == 2

    def test_get_next_empty(self, tmp_cwd):
        session = create_session("test", cwd=str(tmp_cwd))
        assert session.get_next() is None

    def test_get_interrupted(self, tmp_cwd):
        session = create_session("test", cwd=str(tmp_cwd))
        c = session.add_command("failing cmd")
        c.status = "interrupted"
        assert session.get_interrupted().id == c.id

    def test_get_remaining(self, tmp_cwd):
        session = create_session("test", cwd=str(tmp_cwd))
        session.add_command("echo 1")
        session.add_command("echo 2")
        session.commands[0].status = "done"
        remaining = session.get_remaining()
        assert len(remaining) == 1
        assert remaining[0].id == 2

    def test_summary(self, tmp_cwd):
        session = create_session("test", cwd=str(tmp_cwd))
        session.add_command("a")
        session.add_command("b")
        session.commands[0].status = "done"
        counts = session.summary()
        assert counts["done"] == 1
        assert counts["pending"] == 1

    def test_list_sessions(self, tmp_cwd):
        create_session("first", cwd=str(tmp_cwd))
        time.sleep(0.01)
        create_session("second", cwd=str(tmp_cwd))
        sessions = list_sessions(cwd=str(tmp_cwd))
        assert len(sessions) == 2

    def test_delete_session(self, tmp_cwd):
        session = create_session("to delete", cwd=str(tmp_cwd))
        assert delete_session(session.id, cwd=str(tmp_cwd))
        assert load_active_session(cwd=str(tmp_cwd)) is None
        assert not delete_session("nonexistent", cwd=str(tmp_cwd))

    def test_persistence(self, tmp_cwd):
        session = create_session("persist", cwd=str(tmp_cwd))
        session.add_command("echo test")
        session.commands[0].status = "done"
        session.commands[0].exit_code = 0
        session.save()

        loaded = load_active_session(cwd=str(tmp_cwd))
        assert loaded.commands[0].status == "done"
        assert loaded.commands[0].exit_code == 0


class TestRunner:
    def test_run_success(self, tmp_cwd):
        session = create_session("test", cwd=str(tmp_cwd))
        cmd = session.add_command("echo hello world")
        run_command(cmd, session)
        assert cmd.status == "done"
        assert cmd.exit_code == 0
        assert any("hello world" in line for line in cmd.last_output)
        assert cmd.duration_seconds is not None

    def test_run_failure(self, tmp_cwd):
        session = create_session("test", cwd=str(tmp_cwd))
        cmd = session.add_command("exit 1")
        run_command(cmd, session)
        assert cmd.status == "interrupted"
        assert cmd.exit_code == 1

    def test_run_captures_output(self, tmp_cwd):
        session = create_session("test", cwd=str(tmp_cwd))
        cmd = session.add_command("for i in 1 2 3 4 5; do echo line$i; done")
        run_command(cmd, session)
        assert cmd.status == "done"
        assert len(cmd.last_output) == 5

    def test_run_saves_to_disk(self, tmp_cwd):
        session = create_session("test", cwd=str(tmp_cwd))
        cmd = session.add_command("echo saved")
        run_command(cmd, session)
        loaded = load_active_session(cwd=str(tmp_cwd))
        assert loaded.commands[0].status == "done"
