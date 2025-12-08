"""Event processor for building session state from log streams."""

from typing import Callable, Optional
from ..models.builder import AgentTreeBuilder
from ..models.session import SessionModel


class EventProcessor:
    """Process log events and build session state."""

    def __init__(self, on_update: Optional[Callable[[SessionModel], None]] = None):
        """Initialize event processor.

        Args:
            on_update: Optional callback called when session state updates.
        """
        self.builder = AgentTreeBuilder()
        self.on_update = on_update

    def process_entry(self, entry: dict) -> None:
        """Process a single log entry.

        Args:
            entry: Parsed JSON log entry.
        """
        self.builder.process_event(entry)

        # Notify callback if registered
        if self.on_update:
            self.on_update(self.builder.session)

    def process_batch(self, entries: list[dict]) -> None:
        """Process a batch of log entries.

        Args:
            entries: List of parsed JSON log entries.
        """
        for entry in entries:
            self.builder.process_event(entry)

        # Notify callback after batch
        if self.on_update:
            self.on_update(self.builder.session)

    def get_session(self) -> SessionModel:
        """Get the current session state.

        Returns:
            Current SessionModel.
        """
        return self.builder.build()

    def reset(self) -> None:
        """Reset the processor to start fresh."""
        self.builder = AgentTreeBuilder()
