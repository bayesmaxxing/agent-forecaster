"""Event data models for timeline visualization."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class TimelineEvent:
    """Represents a point-in-time event in the agent execution."""
    timestamp: datetime
    event_type: str
    agent_name: Optional[str]
    agent_type: Optional[str]
    level: str
    data: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None  # Session ID from top-level field

    # For timeline visualization
    duration: Optional[float] = None  # Duration in seconds (for spans)
    track_index: int = 0  # Which timeline track to render on

    @classmethod
    def from_json_entry(cls, entry: Dict[str, Any]) -> "TimelineEvent":
        """Create a TimelineEvent from a JSONL log entry."""
        timestamp_str = entry.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            timestamp = datetime.now()

        return cls(
            timestamp=timestamp,
            event_type=entry.get("event_type", "unknown"),
            agent_name=entry.get("agent_name"),
            agent_type=entry.get("agent_type"),
            level=entry.get("level", "info"),
            data=entry.get("data", {}),
            session_id=entry.get("session_id")  # Capture top-level session_id
        )


@dataclass
class ToolCallSpan:
    """Represents a tool call with start and end time for timeline visualization."""
    tool_name: str
    agent_name: str
    start_time: datetime
    end_time: Optional[datetime] = None  # None if still running
    params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    is_error: bool = False
    tool_call_id: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        """Calculate duration in seconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()

    @property
    def is_complete(self) -> bool:
        """Check if tool call has completed."""
        return self.end_time is not None


@dataclass
class LLMCallMarker:
    """Represents an LLM API call for timeline visualization."""
    agent_name: str
    timestamp: datetime
    model: str
    content: Optional[str] = None
    reasoning: Optional[str] = None
    tokens_total: Optional[int] = None
    tokens_prompt: Optional[int] = None
    tokens_completion: Optional[int] = None

    @classmethod
    def from_event(cls, event: TimelineEvent) -> Optional["LLMCallMarker"]:
        """Create LLMCallMarker from a timeline event."""
        if event.event_type != "llm_response":
            return None

        data = event.data
        tokens = data.get("tokens", {})

        return cls(
            agent_name=event.agent_name or "unknown",
            timestamp=event.timestamp,
            model=data.get("model", "unknown"),
            content=data.get("content"),
            reasoning=data.get("reasoning"),
            tokens_total=tokens.get("total") if isinstance(tokens, dict) else None,
            tokens_prompt=tokens.get("prompt") if isinstance(tokens, dict) else None,
            tokens_completion=tokens.get("completion") if isinstance(tokens, dict) else None,
        )
