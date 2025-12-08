"""Event list widget for displaying session events."""

from rich.text import Text
from textual.widgets import DataTable
from ..models.events import TimelineEvent
from ..models.session import SessionModel


class EventListWidget(DataTable):
    """Widget for displaying a list of events."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session: SessionModel | None = None
        self.cursor_type = "row"

    def on_mount(self) -> None:
        """Setup columns when widget is mounted."""
        self.add_columns("Time", "Type", "Agent", "Details")

    def update_from_session(self, session: SessionModel) -> None:
        """Update the event list from session data."""
        self.session = session
        self.rebuild_list()

    def rebuild_list(self) -> None:
        """Rebuild the entire event list."""
        if not self.session:
            return

        self.clear()

        for event in self.session.events:
            self._add_event_row(event)

    def _add_event_row(self, event: TimelineEvent) -> None:
        """Add a single event row to the table."""
        # Format time
        time_str = event.timestamp.strftime("%H:%M:%S.%f")[:-3]  # Millisecond precision

        # Event type with color
        type_text = self._format_event_type(event.event_type)

        # Agent name
        agent_str = event.agent_name or "-"

        # Details
        details = self._format_details(event)

        self.add_row(time_str, type_text, agent_str, details)

    def _format_event_type(self, event_type: str) -> Text:
        """Format event type with color."""
        colors = {
            "llm_response": "yellow",
            "tool_call": "blue",
            "tool_result": "cyan",
            "agent_action": "green",
            "subagent_lifecycle": "magenta",
            "execution_summary": "bright_green",
            "session_start": "bright_white",
            "session_end": "bright_white",
            "cycle": "white",
            "error": "red",
        }

        color = colors.get(event_type, "white")
        return Text(event_type, style=color)

    def _format_details(self, event: TimelineEvent) -> str:
        """Format event details for display."""
        event_type = event.event_type
        data = event.data

        if event_type == "tool_call":
            tool_name = data.get("tool_name", "unknown")
            return f"Tool: {tool_name}"

        elif event_type == "tool_result":
            tool_name = data.get("tool_name", "unknown")
            is_error = data.get("is_error", False)
            status = "ERROR" if is_error else "OK"
            return f"{tool_name} -> {status}"

        elif event_type == "llm_response":
            model = data.get("model", "unknown")
            tokens = data.get("tokens", {})
            if isinstance(tokens, dict):
                total = tokens.get("total", 0)
                return f"Model: {model} ({total} tokens)"
            return f"Model: {model}"

        elif event_type == "agent_action":
            action = data.get("action", "")
            return action

        elif event_type == "subagent_lifecycle":
            action = data.get("action", "")
            return action

        elif event_type == "execution_summary":
            iterations = data.get("iterations", 0)
            tokens = data.get("tokens", 0)
            success = data.get("success", False)
            status = "✓" if success else "✗"
            return f"{status} {iterations} iter, {tokens} tokens"

        elif event_type == "cycle":
            cycle_num = data.get("cycle_number", 0)
            return f"Cycle {cycle_num}"

        return ""

    def get_selected_event(self) -> TimelineEvent | None:
        """Get the currently selected event."""
        if not self.session or self.cursor_row is None:
            return None

        if 0 <= self.cursor_row < len(self.session.events):
            return self.session.events[self.cursor_row]

        return None
