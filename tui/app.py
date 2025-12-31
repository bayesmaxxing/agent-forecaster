"""Main Textual TUI application."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static
from .screens.session_picker import SessionPickerScreen
from .screens.help_screen import HelpScreen
from .screens.filter_screen import FilterScreen
from .widgets.agent_tree import AgentTreeWidget
from .widgets.event_list import EventListWidget
from .widgets.timeline import Timeline
from .widgets.event_inspector import EventInspector
from .widgets.metrics_panel import MetricsPanel
from .streams import LogReader, EventProcessor
from .models.session import SessionModel


class MainScreen(Container):
    """Main screen showing agent tree, timeline, and event inspector."""

    def compose(self) -> ComposeResult:
        """Compose the main screen layout."""
        with Horizontal():
            # Left panel: Agent tree
            with Vertical(id="left-panel"):
                yield Static("Agent Hierarchy", id="tree-title")
                yield AgentTreeWidget(id="agent-tree")

            # Right panels
            with Vertical(id="right-panels"):
                # Top right: Timeline
                with Vertical(id="timeline-panel"):
                    yield Static("Timeline (Gantt View) - Use +/- to zoom, h/l to pan", id="timeline-title")
                    yield Timeline(id="timeline")

                # Bottom right: Event inspector
                with Vertical(id="inspector-panel"):
                    yield Static("Event Inspector", id="inspector-title")
                    yield EventInspector(id="event-inspector")


class AgentForecasterTUI(App):
    """TUI application for visualizing multi-agent forecaster sessions."""

    TITLE = "Agent Forecaster TUI"

    CSS = """
    Screen {
        background: $surface;
    }

    #tree-title, #timeline-title, #inspector-title {
        text-align: center;
        background: $primary;
        padding: 0 1;
        width: 100%;
    }

    #left-panel {
        width: 25%;
        border-right: solid $primary;
    }

    #right-panels {
        width: 75%;
    }

    #timeline-panel {
        height: 60%;
        border-bottom: solid $primary;
    }

    #inspector-panel {
        height: 40%;
    }

    #agent-tree {
        height: 100%;
        width: 100%;
    }

    #timeline {
        height: 100%;
        width: 100%;
        border: solid $primary;
    }

    #event-inspector {
        height: 100%;
        width: 100%;
    }

    Horizontal {
        height: 100%;
    }

    Vertical {
        height: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "reload", "Reload"),
        Binding("s", "switch_session", "Switch Session"),
        Binding("f1", "help", "Help"),
        Binding("?", "help", "Help"),
        Binding("f", "filter", "Filter Events"),
        Binding("/", "search", "Search"),
    ]

    def __init__(self, session_id: str | None = None, live_mode: bool = False):
        super().__init__()
        self.session_id = session_id
        self.live_mode = live_mode
        self.session: SessionModel | None = None
        self.log_path: str | None = None

    def on_mount(self) -> None:
        """Handle app mounting."""
        if self.session_id:
            # Load specified session
            self.load_session(self.session_id)
        else:
            # Show session picker
            self.push_screen(SessionPickerScreen(), self.on_session_selected)

    def on_session_selected(self, session_info: dict | None) -> None:
        """Handle session selection from picker."""
        if session_info:
            self.session_id = session_info["session_id"]
            self.log_path = session_info["path"]
            self.load_session_from_path(self.log_path)

    def load_session(self, session_id: str) -> None:
        """Load a session by ID."""
        from .streams import SessionFinder

        finder = SessionFinder()
        log_path = finder.find_session(session_id)

        if log_path:
            self.log_path = log_path
            self.load_session_from_path(log_path)
        else:
            self.notify(f"Session not found: {session_id}", severity="error")

    def load_session_from_path(self, log_path: str) -> None:
        """Load a session from a log file path."""
        try:
            # Read log file
            reader = LogReader(log_path)
            entries = reader.read_all()

            # Process events
            processor = EventProcessor()
            processor.process_batch(entries)
            self.session = processor.get_session()

            # Update UI
            self.update_ui()

            self.notify(f"Loaded session: {self.session.session_id}")

        except Exception as e:
            self.notify(f"Error loading session: {e}", severity="error")

    def update_ui(self) -> None:
        """Update all UI components with current session data."""
        if not self.session:
            return

        # Update title
        self.title = f"Agent Forecaster TUI - {self.session.session_id}"

        # Update widgets
        try:
            agent_tree = self.query_one("#agent-tree", AgentTreeWidget)
            agent_tree.update_from_session(self.session)
        except:
            pass  # Widget not yet mounted

        try:
            timeline = self.query_one("#timeline", Timeline)
            timeline.update_from_session(self.session)
        except:
            pass  # Widget not yet mounted

        try:
            event_list = self.query_one("#event-list", EventListWidget)
            event_list.update_from_session(self.session)
        except:
            pass  # Widget not yet mounted

    def on_tree_node_highlighted(self, event) -> None:
        """Handle agent tree node selection."""
        try:
            agent_tree = self.query_one("#agent-tree", AgentTreeWidget)
            agent = agent_tree.get_selected_agent()

            if agent:
                inspector = self.query_one("#event-inspector", EventInspector)
                inspector.show_agent(agent)
        except:
            pass

    def compose(self) -> ComposeResult:
        """Compose the app UI."""
        yield Header()
        yield MainScreen()
        yield Footer()

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_reload(self) -> None:
        """Reload the current session."""
        if self.log_path:
            self.load_session_from_path(self.log_path)

    def action_switch_session(self) -> None:
        """Switch to a different session."""
        self.push_screen(SessionPickerScreen(), self.on_session_selected)

    def action_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())

    def action_filter(self) -> None:
        """Show filter screen."""
        self.push_screen(FilterScreen(), self.on_filter_applied)

    def on_filter_applied(self, filters: dict | None) -> None:
        """Handle filter application."""
        if filters:
            # Apply filters to event list (to be implemented)
            self.notify(f"Filters applied: {len(filters)} active")
        else:
            self.notify("Filters cleared")

    def action_search(self) -> None:
        """Show search dialog."""
        # Placeholder for search functionality
        self.notify("Search feature coming in Phase 4", severity="information")


def run_tui(session_id: str | None = None, live_mode: bool = False):
    """Run the TUI application.

    Args:
        session_id: Optional session ID to load directly.
        live_mode: If True, tail the log file for real-time updates.
    """
    app = AgentForecasterTUI(session_id=session_id, live_mode=live_mode)
    app.run()
