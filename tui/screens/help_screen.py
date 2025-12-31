"""Help screen showing keyboard shortcuts and usage information."""

from rich.text import Text
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static
from textual.containers import VerticalScroll, Container
from textual.binding import Binding


class HelpScreen(ModalScreen):
    """Modal screen displaying help and keyboard shortcuts."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close Help"),
        Binding("q", "dismiss", "Close Help"),
    ]

    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-container {
        width: 80;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #help-title {
        text-align: center;
        text-style: bold;
        background: $primary;
        padding: 1;
        margin-bottom: 1;
    }

    #help-content {
        height: auto;
        max-height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the help screen."""
        with Container(id="help-container"):
            yield Static("Agent Forecaster TUI - Help", id="help-title")
            yield VerticalScroll(self._build_help_content(), id="help-content")

    def _build_help_content(self) -> Static:
        """Build the help content."""
        content = Text()

        # Global shortcuts
        content.append("═" * 60 + "\n", style="bold cyan")
        content.append("GLOBAL SHORTCUTS\n", style="bold yellow")
        content.append("═" * 60 + "\n\n", style="bold cyan")

        shortcuts = [
            ("q", "Quit application"),
            ("F1, ?", "Show this help screen"),
            ("r", "Reload current session"),
            ("s", "Switch to different session"),
            ("Tab", "Cycle focus between panels"),
            ("Shift+Tab", "Reverse cycle focus"),
        ]

        for key, desc in shortcuts:
            content.append(f"  {key:<15}", style="bold green")
            content.append(f"{desc}\n")

        content.append("\n")

        # Navigation shortcuts
        content.append("═" * 60 + "\n", style="bold cyan")
        content.append("NAVIGATION\n", style="bold yellow")
        content.append("═" * 60 + "\n\n", style="bold cyan")

        nav_shortcuts = [
            ("j, ↓", "Move selection down"),
            ("k, ↑", "Move selection up"),
            ("g", "Jump to top"),
            ("G", "Jump to bottom"),
            ("Ctrl+f", "Page down"),
            ("Ctrl+b", "Page up"),
        ]

        for key, desc in nav_shortcuts:
            content.append(f"  {key:<15}", style="bold green")
            content.append(f"{desc}\n")

        content.append("\n")

        # Agent Tree shortcuts
        content.append("═" * 60 + "\n", style="bold cyan")
        content.append("AGENT TREE PANEL\n", style="bold yellow")
        content.append("═" * 60 + "\n\n", style="bold cyan")

        tree_shortcuts = [
            ("Enter", "Expand/collapse agent node"),
            ("Space", "Select agent (show in inspector)"),
        ]

        for key, desc in tree_shortcuts:
            content.append(f"  {key:<15}", style="bold green")
            content.append(f"{desc}\n")

        content.append("\n")

        # Timeline shortcuts
        content.append("═" * 60 + "\n", style="bold cyan")
        content.append("TIMELINE PANEL\n", style="bold yellow")
        content.append("═" * 60 + "\n\n", style="bold cyan")

        timeline_shortcuts = [
            ("+, =", "Zoom in"),
            ("-", "Zoom out"),
            ("0", "Reset zoom to default"),
            ("h, ←", "Pan left"),
            ("l, →", "Pan right"),
        ]

        for key, desc in timeline_shortcuts:
            content.append(f"  {key:<15}", style="bold green")
            content.append(f"{desc}\n")

        content.append("\n")

        # Visual Legend
        content.append("═" * 60 + "\n", style="bold cyan")
        content.append("VISUAL LEGEND\n", style="bold yellow")
        content.append("═" * 60 + "\n\n", style="bold cyan")

        content.append("Agent States:\n", style="bold")
        states = [
            ("✓", "Completed successfully", "green"),
            ("✗", "Failed", "red"),
            ("⟳", "Running", "yellow"),
            ("⋯", "Waiting for tool result", "cyan"),
            ("○", "Created but not started", "white"),
        ]

        for icon, desc, color in states:
            content.append(f"  {icon} ", style=f"bold {color}")
            content.append(f"{desc}\n")

        content.append("\n")

        content.append("Timeline Elements:\n", style="bold")
        timeline_elements = [
            ("█", "Agent execution span", "green"),
            ("▬", "Tool call (successful)", "blue"),
            ("▓", "Tool call (error)", "red"),
            ("◆", "LLM API call", "yellow"),
        ]

        for symbol, desc, color in timeline_elements:
            content.append(f"  {symbol} ", style=f"bold {color}")
            content.append(f"{desc}\n")

        content.append("\n")

        # Usage Tips
        content.append("═" * 60 + "\n", style="bold cyan")
        content.append("USAGE TIPS\n", style="bold yellow")
        content.append("═" * 60 + "\n\n", style="bold cyan")

        tips = [
            "• Select an agent in the tree to see detailed metrics in the inspector",
            "• Use the timeline to visualize parallel agent execution and tool calls",
            "• Zoom in on the timeline to see more details of rapid events",
            "• Pan the timeline to navigate through long sessions",
            "• The event inspector shows full details including reasoning and parameters",
        ]

        for tip in tips:
            content.append(f"{tip}\n\n")

        # About
        content.append("═" * 60 + "\n", style="bold cyan")
        content.append("ABOUT\n", style="bold yellow")
        content.append("═" * 60 + "\n\n", style="bold cyan")

        content.append("Agent Forecaster TUI v0.2 (Phase 3)\n")
        content.append("Built with Textual framework\n")
        content.append("GitHub: anthropics/claude-code\n\n")

        content.append("Press ", style="dim")
        content.append("ESC", style="bold green")
        content.append(" or ", style="dim")
        content.append("q", style="bold green")
        content.append(" to close this help screen\n", style="dim")

        return Static(content)

    def action_dismiss(self) -> None:
        """Dismiss the help screen."""
        self.dismiss()
