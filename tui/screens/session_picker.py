"""Session picker screen for selecting log files to view."""

from datetime import datetime
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Static
from textual.binding import Binding
from ..streams import SessionFinder


class SessionPickerScreen(Screen):
    """Screen for selecting a session log file to view."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "select", "Select Session"),
        Binding("r", "refresh", "Refresh"),
    ]

    CSS = """
    SessionPickerScreen {
        align: center middle;
    }

    #session-title {
        text-align: center;
        width: 100%;
        padding: 1;
        background: $primary;
    }

    #session-table {
        width: 90%;
        height: 80%;
        margin: 2 5;
    }
    """

    def __init__(self, logs_dir: str = "logs"):
        super().__init__()
        self.finder = SessionFinder(logs_dir)
        self.sessions = []

    def compose(self) -> ComposeResult:
        """Compose the session picker UI."""
        yield Header()
        yield Static("Select a Session to View", id="session-title")
        yield DataTable(id="session-table")
        yield Footer()

    def on_mount(self) -> None:
        """Setup the session picker when mounted."""
        table = self.query_one("#session-table", DataTable)

        # Add columns
        table.add_columns("Session ID", "Date", "Time", "Size")
        table.cursor_type = "row"

        # Load sessions
        self.load_sessions()

        # Focus the table so keyboard navigation works
        table.focus()

    def load_sessions(self) -> None:
        """Load and display available sessions."""
        table = self.query_one("#session-table", DataTable)
        table.clear()

        self.sessions = self.finder.list_sessions()

        if not self.sessions:
            table.add_row("No sessions found", "", "", "")
            return

        for session_info in self.sessions:
            session_id = session_info["session_id"]
            modified = session_info["modified"]
            size = session_info["size"]

            # Format timestamp
            dt = datetime.fromtimestamp(modified)
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M:%S")

            # Format size
            if size < 1024:
                size_str = f"{size}B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f}KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f}MB"

            table.add_row(session_id, date_str, time_str, size_str)

    def action_refresh(self) -> None:
        """Refresh the session list."""
        self.load_sessions()

    def action_select(self) -> None:
        """Select the highlighted session."""
        table = self.query_one("#session-table", DataTable)

        if not self.sessions:
            self.app.notify("No sessions available", severity="warning")
            return

        # Get selected row index
        cursor_row = table.cursor_row

        # DataTable cursor_row is 0-indexed
        if cursor_row is None:
            self.app.notify("No row selected", severity="warning")
            return

        if cursor_row >= len(self.sessions):
            self.app.notify("Invalid selection", severity="error")
            return

        selected_session = self.sessions[cursor_row]
        self.dismiss(selected_session)

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
