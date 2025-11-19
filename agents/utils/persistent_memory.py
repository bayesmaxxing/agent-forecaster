"""Persistent memory system for agent coordination and persistence."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import threading


@dataclass
class PersistentMemoryEntry:
    """A single entry in the persistent memory system."""
    id: str
    category: str
    title: str
    content: str
    metadata: Dict[str, Any]
    timestamp: str
    tags: List[str]
    agent_name: str = "unknown"
    task_id: str = "default"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersistentMemoryEntry":
        """Create from dictionary."""
        return cls(**data)


class PersistentMemory:
    """Thread-safe persistent memory system with file persistence."""

    def __init__(self, memory_dir: str = "persistent_memory", auto_persist: bool = True):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.auto_persist = auto_persist

        # In-memory storage
        self._memory: Dict[str, PersistentMemoryEntry] = {}
        self._lock = threading.RLock()

        # Load existing data
        self._load_from_disk()

    def _generate_id(self) -> str:
        """Generate unique ID for persistent memory entry."""
        return f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    def _load_from_disk(self) -> None:
        """Load all persistent memory entries from disk."""
        for file_path in self.memory_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    entry = PersistentMemoryEntry.from_dict(data)
                    self._memory[entry.id] = entry
            except Exception as e:
                print(f"Warning: Failed to load persistent memory file {file_path}: {e}")

    def _persist_entry(self, entry: PersistentMemoryEntry) -> None:
        """Persist a single entry to disk."""
        if not self.auto_persist:
            return

        file_path = self.memory_dir / f"{entry.id}.json"
        try:
            with open(file_path, 'w') as f:
                json.dump(entry.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to persist persistent memory entry {entry.id}: {e}")

    def store(
        self,
        agent_name: str,
        task_id: str,
        category: str,
        title: str,
        content: str,
        metadata: Dict[str, Any] = None,
        tags: List[str] = None
    ) -> str:
        """Store a new memory entry."""
        with self._lock:
            entry_id = self._generate_id()
            entry = PersistentMemoryEntry(
                id=entry_id,
                category=category,
                title=title,
                content=content,
                metadata=metadata or {},
                timestamp=datetime.now().isoformat(),
                tags=tags or [],
                agent_name=agent_name,
                task_id=task_id
            )

            self._memory[entry_id] = entry
            self._persist_entry(entry)

            return entry_id

    def get(self, entry_id: str) -> Optional[PersistentMemoryEntry]:
        """Get a specific memory entry by ID."""
        with self._lock:
            return self._memory.get(entry_id)

    def search(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        content_contains: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[PersistentMemoryEntry]:
        """Search persistent memory entries with various filters."""
        with self._lock:
            results = []

            for entry in self._memory.values():
                # Apply filters
                if category and entry.category != category:
                    continue
                if tags and not any(tag in entry.tags for tag in tags):
                    continue
                if content_contains and content_contains.lower() not in entry.content.lower():
                    continue

                results.append(entry)

            # Sort by timestamp (newest first)
            results.sort(key=lambda x: x.timestamp, reverse=True)

            # Apply limit
            if limit:
                results = results[:limit]

            return results

    def get_recent(self, limit: int = 10) -> List[PersistentMemoryEntry]:
        """Get the most recent memory entries."""
        return self.search(limit=limit)

    def get_by_category(self, category: str, limit: Optional[int] = None) -> List[PersistentMemoryEntry]:
        """Get all entries in a specific category."""
        return self.search(category=category, limit=limit)

    def update(self, entry_id: str, **updates) -> bool:
        """Update an existing persistent memory entry."""
        with self._lock:
            entry = self._memory.get(entry_id)
            if not entry:
                return False

            # Update allowed fields
            allowed_updates = ['title', 'content', 'metadata', 'tags']
            for key, value in updates.items():
                if key in allowed_updates:
                    setattr(entry, key, value)

            # Update timestamp
            entry.timestamp = datetime.now().isoformat()

            self._persist_entry(entry)
            return True

    def delete(self, entry_id: str) -> bool:
        """Delete a persistent memory entry."""
        with self._lock:
            if entry_id not in self._memory:
                return False

            del self._memory[entry_id]

            # Remove from disk
            file_path = self.memory_dir / f"{entry_id}.json"
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    print(f"Warning: Failed to delete memory file {file_path}: {e}")

            return True

# Global shared memory instance
_persistent_memory_instance: Optional[PersistentMemory] = None


def get_persistent_memory() -> PersistentMemory:
    """Get the global persistent memory instance."""
    global _persistent_memory_instance
    if _persistent_memory_instance is None:
        _persistent_memory_instance = PersistentMemory()
    return _persistent_memory_instance


def init_persistent_memory(memory_dir: str = "persistent_memory", auto_persist: bool = True) -> PersistentMemory:
    """Initialize the global persistent memory instance with custom settings."""
    global _persistent_memory_instance
    _persistent_memory_instance = PersistentMemory(memory_dir=memory_dir, auto_persist=auto_persist)
    return _persistent_memory_instance