"""Main Textual TUI application."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static
from .screens.session_picker import SessionPickerScreen
from .widgets.agent_tree import AgentTreeWidget
from .widgets.event_list import EventListWidget
from .streams import LogReader, EventProcessor
from .models.session import SessionModel


class MainScreen(Container):
    """Main screen showing agent tree and event list."""

    def compose(self) -> ComposeResult:
        """Compose the main screen layout."""
        with Horizontal():
            # Left panel: Agent tree
            with Vertical(id="left-panel"):
                yield Static("Agent Hierarchy", id="tree-title")
                yield AgentTreeWidget(id="agent-tree")

            # Right panel: Event list
            with Vertical(id="right-panel"):
                yield Static("Events", id="event-title")
                yield EventListWidget(id="event-list")


class AgentForecasterTUI(App):
    """TUI application for visualizing multi-agent forecaster sessions."""

    TITLE = "Agent Forecaster TUI"

    CSS = """
    Screen {
        background: $surface;
    }

    #tree-title, #event-title {
        text-align: center;
        background: $primary;
        padding: 0 1;
        width: 100%;
    }

    #left-panel {
        width: 30%;
        border-right: solid $primary;
    }

    #right-panel {
        width: 70%;
    }

    #agent-tree {
        height: 100%;
        width: 100%;
    }

    #event-list {
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
            event_list = self.query_one("#event-list", EventListWidget)
            event_list.update_from_session(self.session)
        except:
            pass  # Widget not yet mounted

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


def run_tui(session_id: str | None = None, live_mode: bool = False):
    """Run the TUI application.

    Args:
        session_id: Optional session ID to load directly.
        live_mode: If True, tail the log file for real-time updates.
    """
    app = AgentForecasterTUI(session_id=session_id, live_mode=live_mode)
    app.run()
