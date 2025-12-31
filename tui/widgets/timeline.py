"""Timeline widget for Gantt-style visualization of agent execution."""

from datetime import datetime, timedelta
from typing import Optional
from rich.text import Text
from rich.style import Style
from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message
from ..models.session import SessionModel, AgentNode
from ..models.events import ToolCallSpan, LLMCallMarker
from ..models.builder import TimelineBuilder


class Timeline(Widget):
    """Gantt-style timeline visualization widget."""

    # Reactive properties
    zoom_level = reactive(1.0)  # 1.0 = normal, >1 = zoomed in, <1 = zoomed out
    pan_offset = reactive(0.0)  # Seconds offset from start
    selected_item = reactive(None)  # Selected span or marker

    class ItemSelected(Message):
        """Message sent when a timeline item is selected."""

        def __init__(self, item_type: str, item_data: dict):
            super().__init__()
            self.item_type = item_type
            self.item_data = item_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session: Optional[SessionModel] = None
        self.builder: Optional[TimelineBuilder] = None
        self.tracks: dict[str, int] = {}
        self.min_time: Optional[datetime] = None
        self.max_time: Optional[datetime] = None
        self.can_focus = True

    def update_from_session(self, session: SessionModel) -> None:
        """Update timeline from session data."""
        self.session = session
        self.builder = TimelineBuilder(session)
        self.tracks = self.builder.assign_tracks()

        # Calculate time range
        self._calculate_time_range()
        self.refresh()

    def _calculate_time_range(self) -> None:
        """Calculate min and max timestamps in the session."""
        if not self.session:
            return

        timestamps = []

        # Collect all timestamps
        if self.session.start_time:
            timestamps.append(self.session.start_time)
        if self.session.end_time:
            timestamps.append(self.session.end_time)

        for event in self.session.events:
            timestamps.append(event.timestamp)

        for tool_call in self.session.tool_calls:
            timestamps.append(tool_call.start_time)
            if tool_call.end_time:
                timestamps.append(tool_call.end_time)

        if timestamps:
            self.min_time = min(timestamps)
            self.max_time = max(timestamps)

            # Add small padding
            if self.max_time == self.min_time:
                self.max_time = self.min_time + timedelta(seconds=1)

    def render(self) -> Text:
        """Render the timeline."""
        if not self.session or not self.min_time or not self.max_time:
            return Text("No data to display", style="dim")

        lines = []
        width = self.size.width - 2  # Account for borders

        # Calculate visible time range based on zoom and pan
        total_duration = (self.max_time - self.min_time).total_seconds()
        visible_duration = total_duration / self.zoom_level
        view_start = self.min_time + timedelta(seconds=self.pan_offset)
        view_end = view_start + timedelta(seconds=visible_duration)

        # Render time axis
        time_axis = self._render_time_axis(view_start, view_end, width)

        # Render tracks
        hierarchy = self.session.get_agent_hierarchy()

        for agent, depth in hierarchy:
            track_line = self._render_track(
                agent, depth, view_start, view_end, width
            )
            lines.append(track_line)

        # Add time axis at bottom
        lines.append(Text("─" * width, style="dim"))
        lines.append(time_axis)

        return Text("\n").join(lines)

    def _render_time_axis(
        self, view_start: datetime, view_end: datetime, width: int
    ) -> Text:
        """Render the time axis with labels."""
        duration = (view_end - view_start).total_seconds()

        axis = Text()

        # Determine label interval based on duration
        if duration < 10:  # Less than 10 seconds
            interval = 1
            fmt = "%H:%M:%S.%f"
        elif duration < 60:  # Less than 1 minute
            interval = 5
            fmt = "%H:%M:%S"
        elif duration < 600:  # Less than 10 minutes
            interval = 30
            fmt = "%H:%M:%S"
        else:
            interval = 60
            fmt = "%H:%M"

        # Calculate positions for labels
        current_time = view_start
        positions = []

        while current_time <= view_end:
            pos = self._time_to_position(current_time, view_start, view_end, width)
            if 0 <= pos < width:
                label = current_time.strftime(fmt)
                if duration < 10:
                    label = label[:-3]  # Trim microseconds to milliseconds
                positions.append((pos, label))
            current_time += timedelta(seconds=interval)

        # Build axis string
        axis_chars = [" "] * width
        for pos, label in positions:
            # Mark position
            if pos < width:
                axis_chars[pos] = "|"

            # Add label (centered on position)
            label_start = max(0, pos - len(label) // 2)
            label_end = min(width, label_start + len(label))
            label_to_write = label[:label_end - label_start]

            for i, char in enumerate(label_to_write):
                idx = label_start + i
                if 0 <= idx < width:
                    axis_chars[idx] = char

        axis.append("".join(axis_chars), style="cyan")
        return axis

    def _render_track(
        self,
        agent: AgentNode,
        depth: int,
        view_start: datetime,
        view_end: datetime,
        width: int,
    ) -> Text:
        """Render a single agent track."""
        line = Text()

        # Agent label with indentation
        indent = "  " * depth
        prefix = "├─" if depth > 0 else ""
        label = f"{indent}{prefix}{agent.name[:15]:<15}"
        line.append(label, style="bold")
        line.append(" ")

        # Timeline bar
        bar_width = width - len(label) - 1
        bar_chars = [" "] * bar_width

        # Draw agent execution span
        if agent.start_time and agent.end_time:
            start_pos = self._time_to_position(
                agent.start_time, view_start, view_end, bar_width
            )
            end_pos = self._time_to_position(
                agent.end_time, view_start, view_end, bar_width
            )

            for i in range(max(0, start_pos), min(bar_width, end_pos)):
                bar_chars[i] = "█"

        # Draw tool calls for this agent
        if self.builder:
            tool_spans = [
                (span, track_idx)
                for span, track_idx in self.builder.get_tool_call_spans()
                if span.agent_name == agent.name
            ]

            for span, _ in tool_spans:
                if span.start_time:
                    start_pos = self._time_to_position(
                        span.start_time, view_start, view_end, bar_width
                    )

                    if span.end_time:
                        end_pos = self._time_to_position(
                            span.end_time, view_start, view_end, bar_width
                        )
                    else:
                        end_pos = start_pos + 1

                    # Draw tool call span
                    char = "▬" if not span.is_error else "▓"
                    for i in range(max(0, start_pos), min(bar_width, end_pos)):
                        bar_chars[i] = char

        # Draw LLM calls for this agent
        if self.builder:
            llm_markers = [
                (marker, track_idx)
                for marker, track_idx in self.builder.get_llm_markers()
                if marker.agent_name == agent.name
            ]

            for marker, _ in llm_markers:
                pos = self._time_to_position(
                    marker.timestamp, view_start, view_end, bar_width
                )
                if 0 <= pos < bar_width:
                    bar_chars[pos] = "◆"

        # Apply coloring
        bar_text = "".join(bar_chars)

        # Color based on agent state
        if agent.state.value == "completed":
            style = "green"
        elif agent.state.value == "failed":
            style = "red"
        elif agent.state.value == "running":
            style = "yellow"
        else:
            style = "dim"

        line.append(bar_text, style=style)
        return line

    def _time_to_position(
        self,
        time: datetime,
        view_start: datetime,
        view_end: datetime,
        width: int,
    ) -> int:
        """Convert a timestamp to a position in the timeline."""
        if time < view_start or time > view_end:
            # Out of view
            if time < view_start:
                return -1
            else:
                return width + 1

        duration = (view_end - view_start).total_seconds()
        elapsed = (time - view_start).total_seconds()

        if duration == 0:
            return 0

        position = int((elapsed / duration) * width)
        return max(0, min(width - 1, position))

    def action_zoom_in(self) -> None:
        """Zoom in on the timeline."""
        self.zoom_level = min(self.zoom_level * 1.5, 10.0)
        self.refresh()

    def action_zoom_out(self) -> None:
        """Zoom out on the timeline."""
        self.zoom_level = max(self.zoom_level / 1.5, 0.1)
        self.refresh()

    def action_zoom_reset(self) -> None:
        """Reset zoom to default."""
        self.zoom_level = 1.0
        self.pan_offset = 0.0
        self.refresh()

    def action_pan_left(self) -> None:
        """Pan timeline to the left."""
        if not self.min_time or not self.max_time:
            return

        total_duration = (self.max_time - self.min_time).total_seconds()
        pan_amount = (total_duration / self.zoom_level) * 0.1
        self.pan_offset = max(0, self.pan_offset - pan_amount)
        self.refresh()

    def action_pan_right(self) -> None:
        """Pan timeline to the right."""
        if not self.min_time or not self.max_time:
            return

        total_duration = (self.max_time - self.min_time).total_seconds()
        pan_amount = (total_duration / self.zoom_level) * 0.1
        max_offset = total_duration * (1 - 1/self.zoom_level)
        self.pan_offset = min(max_offset, self.pan_offset + pan_amount)
        self.refresh()

    # Key bindings handled by parent
    async def on_key(self, event) -> None:
        """Handle key events."""
        if event.key == "+":
            self.action_zoom_in()
        elif event.key == "-":
            self.action_zoom_out()
        elif event.key == "0":
            self.action_zoom_reset()
        elif event.key == "h" or event.key == "left":
            self.action_pan_left()
        elif event.key == "l" or event.key == "right":
            self.action_pan_right()
