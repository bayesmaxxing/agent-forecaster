"""JSONL log file reader and tailer."""

import json
import os
from pathlib import Path
from typing import AsyncIterator, Dict, Any, Optional
import asyncio


class LogReader:
    """Read JSONL log files."""

    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self.last_position = 0

    def read_all(self) -> list[Dict[str, Any]]:
        """Read all entries from the log file.

        Returns:
            List of parsed JSON entries.
        """
        entries = []

        if not self.log_path.exists():
            return entries

        with open(self.log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                except json.JSONDecodeError as e:
                    # Skip malformed lines
                    print(f"Warning: Skipping malformed JSON line: {e}")
                    continue

        self.last_position = self.log_path.stat().st_size if self.log_path.exists() else 0
        return entries

    def read_new(self) -> list[Dict[str, Any]]:
        """Read new entries since last read.

        Returns:
            List of new parsed JSON entries.
        """
        entries = []

        if not self.log_path.exists():
            return entries

        with open(self.log_path, 'r') as f:
            # Seek to last position
            f.seek(self.last_position)

            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                except json.JSONDecodeError as e:
                    # Skip malformed lines
                    print(f"Warning: Skipping malformed JSON line: {e}")
                    continue

            # Update position
            self.last_position = f.tell()

        return entries


class LogTailer:
    """Tail JSONL log files in real-time."""

    def __init__(self, log_path: str, poll_interval: float = 0.5):
        """Initialize log tailer.

        Args:
            log_path: Path to the JSONL log file.
            poll_interval: How often to check for new content (seconds).
        """
        self.log_path = Path(log_path)
        self.poll_interval = poll_interval
        self.reader = LogReader(log_path)
        self._stop = False

    async def tail(self) -> AsyncIterator[Dict[str, Any]]:
        """Tail the log file and yield new entries.

        Yields:
            Parsed JSON entries as they are written to the file.
        """
        # First, yield all existing entries
        for entry in self.reader.read_all():
            yield entry

        # Then poll for new entries
        while not self._stop:
            new_entries = self.reader.read_new()

            for entry in new_entries:
                yield entry

            # Wait before next poll
            await asyncio.sleep(self.poll_interval)

    def stop(self):
        """Stop tailing the log file."""
        self._stop = True


class SessionFinder:
    """Find and list available session log files."""

    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)

    def list_sessions(self) -> list[Dict[str, Any]]:
        """List all available session log files.

        Returns:
            List of session info dictionaries with keys:
            - session_id: str
            - path: str
            - size: int (bytes)
            - modified: float (timestamp)
        """
        if not self.logs_dir.exists():
            return []

        sessions = []

        for log_file in self.logs_dir.glob("*.jsonl"):
            session_id = log_file.stem  # Filename without extension
            stat = log_file.stat()

            sessions.append({
                "session_id": session_id,
                "path": str(log_file),
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })

        # Sort by modified time, most recent first
        sessions.sort(key=lambda s: s["modified"], reverse=True)

        return sessions

    def get_latest_session(self) -> Optional[Dict[str, Any]]:
        """Get the most recently modified session.

        Returns:
            Session info dict or None if no sessions exist.
        """
        sessions = self.list_sessions()
        return sessions[0] if sessions else None

    def find_session(self, session_id: str) -> Optional[str]:
        """Find the log file path for a given session ID.

        Args:
            session_id: The session ID to search for.

        Returns:
            Path to the log file or None if not found.
        """
        log_file = self.logs_dir / f"{session_id}.jsonl"
        return str(log_file) if log_file.exists() else None
