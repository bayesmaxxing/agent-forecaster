"""Metrics panel widget for displaying session statistics."""

from typing import Optional
from rich.text import Text
from rich.table import Table
from textual.widgets import Static
from ..models.session import SessionModel, AgentState


class MetricsPanel(Static):
    """Widget displaying session-level metrics and statistics."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session: Optional[SessionModel] = None

    def update_from_session(self, session: SessionModel) -> None:
        """Update metrics from session data."""
        self.session = session
        self.update(self._render_metrics())

    def _render_metrics(self) -> Table:
        """Render session metrics as a table."""
        if not self.session:
            return Table()

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Metric", style="bold cyan")
        table.add_column("Value", style="white")

        # Session info
        table.add_row("Session ID", self.session.session_id)

        # Duration
        if self.session.duration:
            duration_str = self._format_duration(self.session.duration)
            table.add_row("Duration", duration_str)

        # Agent counts
        total_agents = len(self.session.agents)
        completed = sum(1 for a in self.session.agents.values() if a.state == AgentState.COMPLETED)
        failed = sum(1 for a in self.session.agents.values() if a.state == AgentState.FAILED)
        running = sum(1 for a in self.session.agents.values() if a.state == AgentState.RUNNING)

        table.add_row("Total Agents", str(total_agents))
        table.add_row("  Completed", f"[green]{completed}[/green]")
        if failed > 0:
            table.add_row("  Failed", f"[red]{failed}[/red]")
        if running > 0:
            table.add_row("  Running", f"[yellow]{running}[/yellow]")

        # Token usage
        if self.session.total_tokens > 0:
            tokens_str = self._format_number(self.session.total_tokens)
            table.add_row("Total Tokens", tokens_str)

        # Event counts
        table.add_row("Total Events", str(len(self.session.events)))

        # Tool calls
        total_tools = len(self.session.tool_calls)
        failed_tools = sum(1 for tc in self.session.tool_calls if tc.is_error)
        table.add_row("Tool Calls", str(total_tools))
        if failed_tools > 0:
            table.add_row("  Failed", f"[red]{failed_tools}[/red]")

        # LLM calls
        table.add_row("LLM Calls", str(len(self.session.llm_calls)))

        # Cycles
        if self.session.total_cycles > 0:
            table.add_row("Cycles", str(self.session.total_cycles))

        return table

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

    def _format_number(self, num: int) -> str:
        """Format large numbers with commas."""
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        else:
            return str(num)
