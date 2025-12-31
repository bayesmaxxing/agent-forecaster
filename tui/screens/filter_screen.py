"""Filter screen for filtering events and agents."""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static, Input, Checkbox, Button
from textual.containers import Container, Vertical, Horizontal
from textual.binding import Binding


class FilterScreen(ModalScreen):
    """Modal screen for configuring filters."""

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
    ]

    CSS = """
    FilterScreen {
        align: center middle;
    }

    #filter-container {
        width: 60;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #filter-title {
        text-align: center;
        text-style: bold;
        background: $primary;
        padding: 1;
        margin-bottom: 1;
    }

    #filter-content {
        height: auto;
        padding: 1;
    }

    .filter-section {
        margin-bottom: 1;
        border: solid $primary-lighten-2;
        padding: 1;
    }

    .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    Button {
        margin: 1 1 0 1;
    }
    """

    def __init__(self, current_filters: dict | None = None):
        super().__init__()
        self.filters = current_filters or {
            "agent_name": "",
            "event_types": set(),
            "level": set(),
        }

    def compose(self) -> ComposeResult:
        """Compose the filter screen."""
        with Container(id="filter-container"):
            yield Static("Filter Events", id="filter-title")

            with Vertical(id="filter-content"):
                # Agent filter
                with Container(classes="filter-section"):
                    yield Static("Filter by Agent:", classes="section-title")
                    yield Input(
                        placeholder="Agent name (leave empty for all)",
                        value=self.filters.get("agent_name", ""),
                        id="agent-filter-input"
                    )

                # Event type filters
                with Container(classes="filter-section"):
                    yield Static("Filter by Event Type:", classes="section-title")
                    event_types = [
                        "llm_response",
                        "tool_call",
                        "tool_result",
                        "agent_action",
                        "subagent_lifecycle",
                        "execution_summary",
                        "cycle",
                    ]

                    for event_type in event_types:
                        checked = event_type in self.filters.get("event_types", set())
                        yield Checkbox(event_type, checked, id=f"event-type-{event_type}")

                # Level filters
                with Container(classes="filter-section"):
                    yield Static("Filter by Level:", classes="section-title")
                    levels = ["debug", "info", "success", "warning", "error"]

                    for level in levels:
                        checked = level in self.filters.get("level", set())
                        yield Checkbox(level, checked, id=f"level-{level}")

                # Buttons
                with Horizontal():
                    yield Button("Apply", variant="primary", id="apply-button")
                    yield Button("Clear All", id="clear-button")
                    yield Button("Cancel", id="cancel-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "apply-button":
            self._apply_filters()
        elif event.button.id == "clear-button":
            self._clear_filters()
        elif event.button.id == "cancel-button":
            self.dismiss(None)

    def _apply_filters(self) -> None:
        """Apply current filters and dismiss."""
        filters = {}

        # Get agent filter
        agent_input = self.query_one("#agent-filter-input", Input)
        filters["agent_name"] = agent_input.value.strip()

        # Get event type filters
        event_types = set()
        for event_type in ["llm_response", "tool_call", "tool_result", "agent_action",
                           "subagent_lifecycle", "execution_summary", "cycle"]:
            checkbox = self.query_one(f"#event-type-{event_type}", Checkbox)
            if checkbox.value:
                event_types.add(event_type)
        filters["event_types"] = event_types

        # Get level filters
        levels = set()
        for level in ["debug", "info", "success", "warning", "error"]:
            checkbox = self.query_one(f"#level-{level}", Checkbox)
            if checkbox.value:
                levels.add(level)
        filters["level"] = levels

        self.dismiss(filters)

    def _clear_filters(self) -> None:
        """Clear all filters."""
        # Clear agent input
        agent_input = self.query_one("#agent-filter-input", Input)
        agent_input.value = ""

        # Uncheck all event types
        for event_type in ["llm_response", "tool_call", "tool_result", "agent_action",
                           "subagent_lifecycle", "execution_summary", "cycle"]:
            checkbox = self.query_one(f"#event-type-{event_type}", Checkbox)
            checkbox.value = False

        # Uncheck all levels
        for level in ["debug", "info", "success", "warning", "error"]:
            checkbox = self.query_one(f"#level-{level}", Checkbox)
            checkbox.value = False

    def action_dismiss(self) -> None:
        """Dismiss without applying."""
        self.dismiss(None)
