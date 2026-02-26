"""Session management: create, load, save, query commands."""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

TRACKER_DIR = ".gpu-tracker"
ACTIVE_FILE = "active_session.json"


@dataclass
class Command:
    id: int
    cmd: str
    status: str = "pending"  # pending, running, done, interrupted, skipped
    exit_code: Optional[int] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    last_output: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class Session:
    id: str
    name: str
    created_at: str
    cwd: str
    commands: List[Command] = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d["commands"] = [c.to_dict() for c in self.commands]
        return d

    @classmethod
    def from_dict(cls, d):
        commands = [Command.from_dict(c) for c in d.get("commands", [])]
        return cls(
            id=d["id"],
            name=d["name"],
            created_at=d["created_at"],
            cwd=d["cwd"],
            commands=commands,
        )

    def save(self):
        tracker_dir = Path(self.cwd) / TRACKER_DIR
        tracker_dir.mkdir(parents=True, exist_ok=True)
        session_file = tracker_dir / f"{self.id}.json"
        session_file.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))
        # Update active session pointer
        active_file = tracker_dir / ACTIVE_FILE
        active_file.write_text(json.dumps({"active_session": self.id}))

    def add_command(self, cmd: str) -> Command:
        next_id = max((c.id for c in self.commands), default=0) + 1
        command = Command(id=next_id, cmd=cmd)
        self.commands.append(command)
        self.save()
        return command

    def get_next(self) -> Optional[Command]:
        for c in self.commands:
            if c.status == "pending":
                return c
        return None

    def get_interrupted(self) -> Optional[Command]:
        for c in self.commands:
            if c.status == "interrupted":
                return c
        return None

    def get_remaining(self) -> List[Command]:
        return [c for c in self.commands if c.status in ("pending", "interrupted")]

    def skip_interrupted(self) -> List[Command]:
        """Mark all interrupted commands as skipped. Returns the skipped commands."""
        skipped = []
        for c in self.commands:
            if c.status == "interrupted":
                c.status = "skipped"
                skipped.append(c)
        if skipped:
            self.save()
        return skipped

    def summary(self):
        counts = {"pending": 0, "running": 0, "done": 0, "interrupted": 0, "skipped": 0}
        for c in self.commands:
            counts[c.status] = counts.get(c.status, 0) + 1
        return counts


def generate_session_id() -> str:
    now = datetime.now()
    return f"ses_{now.strftime('%Y%m%d_%H%M%S')}_{now.strftime('%f')[:3]}"


def create_session(name: str, cwd: Optional[str] = None) -> Session:
    if cwd is None:
        cwd = os.getcwd()
    session = Session(
        id=generate_session_id(),
        name=name,
        created_at=datetime.now().isoformat(timespec="seconds"),
        cwd=cwd,
    )
    session.save()
    return session


def load_session(session_id: str, cwd: Optional[str] = None) -> Optional[Session]:
    if cwd is None:
        cwd = os.getcwd()
    session_file = Path(cwd) / TRACKER_DIR / f"{session_id}.json"
    if not session_file.exists():
        return None
    data = json.loads(session_file.read_text())
    return Session.from_dict(data)


def load_active_session(cwd: Optional[str] = None) -> Optional[Session]:
    if cwd is None:
        cwd = os.getcwd()
    active_file = Path(cwd) / TRACKER_DIR / ACTIVE_FILE
    if not active_file.exists():
        return None
    data = json.loads(active_file.read_text())
    session_id = data.get("active_session")
    if not session_id:
        return None
    return load_session(session_id, cwd)


def list_sessions(cwd: Optional[str] = None) -> List[Session]:
    if cwd is None:
        cwd = os.getcwd()
    tracker_dir = Path(cwd) / TRACKER_DIR
    if not tracker_dir.exists():
        return []
    sessions = []
    for f in sorted(tracker_dir.glob("ses_*.json")):
        data = json.loads(f.read_text())
        sessions.append(Session.from_dict(data))
    return sessions


def delete_session(session_id: str, cwd: Optional[str] = None) -> bool:
    if cwd is None:
        cwd = os.getcwd()
    session_file = Path(cwd) / TRACKER_DIR / f"{session_id}.json"
    if not session_file.exists():
        return False
    session_file.unlink()
    # If this was the active session, clear the pointer
    active_file = Path(cwd) / TRACKER_DIR / ACTIVE_FILE
    if active_file.exists():
        data = json.loads(active_file.read_text())
        if data.get("active_session") == session_id:
            active_file.unlink()
    return True
