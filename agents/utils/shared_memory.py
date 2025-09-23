"""Shared memory system for agent coordination and persistence."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import threading


@dataclass
class MemoryEntry:
    """A single entry in the shared memory system."""
    id: str
    agent_name: str
    task_id: str
    category: str
    title: str
    content: str
    metadata: Dict[str, Any]
    timestamp: str
    tags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary."""
        return cls(**data)


class SharedMemory:
    """Thread-safe shared memory system with file persistence."""

    def __init__(self, memory_dir: str = "shared_memory", auto_persist: bool = True):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.auto_persist = auto_persist

        # In-memory storage
        self._memory: Dict[str, MemoryEntry] = {}
        self._lock = threading.RLock()

        # Load existing data
        self._load_from_disk()

    def _generate_id(self) -> str:
        """Generate unique ID for memory entry."""
        return f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    def _load_from_disk(self) -> None:
        """Load all memory entries from disk."""
        for file_path in self.memory_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    entry = MemoryEntry.from_dict(data)
                    self._memory[entry.id] = entry
            except Exception as e:
                print(f"Warning: Failed to load memory file {file_path}: {e}")

    def _persist_entry(self, entry: MemoryEntry) -> None:
        """Persist a single entry to disk."""
        if not self.auto_persist:
            return

        file_path = self.memory_dir / f"{entry.id}.json"
        try:
            with open(file_path, 'w') as f:
                json.dump(entry.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to persist memory entry {entry.id}: {e}")

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
            entry = MemoryEntry(
                id=entry_id,
                agent_name=agent_name,
                task_id=task_id,
                category=category,
                title=title,
                content=content,
                metadata=metadata or {},
                timestamp=datetime.now().isoformat(),
                tags=tags or []
            )

            self._memory[entry_id] = entry
            self._persist_entry(entry)

            return entry_id

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory entry by ID."""
        with self._lock:
            return self._memory.get(entry_id)

    def search(
        self,
        agent_name: Optional[str] = None,
        task_id: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        content_contains: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[MemoryEntry]:
        """Search memory entries with various filters."""
        with self._lock:
            results = []

            for entry in self._memory.values():
                # Apply filters
                if agent_name and entry.agent_name != agent_name:
                    continue
                if task_id and entry.task_id != task_id:
                    continue
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

    def get_recent(self, limit: int = 10) -> List[MemoryEntry]:
        """Get the most recent memory entries."""
        return self.search(limit=limit)

    def get_by_category(self, category: str, limit: Optional[int] = None) -> List[MemoryEntry]:
        """Get all entries in a specific category."""
        return self.search(category=category, limit=limit)

    def get_task_history(self, task_id: str) -> List[MemoryEntry]:
        """Get all entries for a specific task."""
        return self.search(task_id=task_id)

    def update(self, entry_id: str, **updates) -> bool:
        """Update an existing memory entry."""
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
        """Delete a memory entry."""
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

    def get_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        with self._lock:
            categories = {}
            agents = {}
            total_size = 0

            for entry in self._memory.values():
                # Count by category
                categories[entry.category] = categories.get(entry.category, 0) + 1

                # Count by agent
                agents[entry.agent_name] = agents.get(entry.agent_name, 0) + 1

                # Rough size calculation
                total_size += len(entry.content) + len(str(entry.metadata))

            return {
                "total_entries": len(self._memory),
                "categories": categories,
                "agents": agents,
                "estimated_size_bytes": total_size,
                "memory_dir": str(self.memory_dir)
            }

    def clear_all(self) -> None:
        """Clear all memory entries (use with caution!)."""
        with self._lock:
            self._memory.clear()

            # Remove all files
            for file_path in self.memory_dir.glob("*.json"):
                try:
                    file_path.unlink()
                except Exception as e:
                    print(f"Warning: Failed to delete memory file {file_path}: {e}")

    def export_task(self, task_id: str, output_file: str) -> bool:
        """Export all entries for a task to a single file."""
        entries = self.get_task_history(task_id)
        if not entries:
            return False

        export_data = {
            "task_id": task_id,
            "export_timestamp": datetime.now().isoformat(),
            "entries": [entry.to_dict() for entry in entries]
        }

        try:
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to export task {task_id}: {e}")
            return False


# Global shared memory instance
_shared_memory_instance: Optional[SharedMemory] = None


def get_shared_memory() -> SharedMemory:
    """Get the global shared memory instance."""
    global _shared_memory_instance
    if _shared_memory_instance is None:
        _shared_memory_instance = SharedMemory()
    return _shared_memory_instance


def init_shared_memory(memory_dir: str = "shared_memory", auto_persist: bool = True) -> SharedMemory:
    """Initialize the global shared memory instance with custom settings."""
    global _shared_memory_instance
    _shared_memory_instance = SharedMemory(memory_dir=memory_dir, auto_persist=auto_persist)
    return _shared_memory_instance