"""Event inspector widget for displaying detailed event information."""

import json
from typing import Optional
from rich.text import Text
from rich.syntax import Syntax
from rich.panel import Panel
from textual.widgets import Static
from textual.containers import VerticalScroll
from ..models.events import TimelineEvent
from ..models.session import AgentNode


class EventInspector(VerticalScroll):
    """Widget for inspecting event details."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_event: Optional[TimelineEvent] = None
        self.current_agent: Optional[AgentNode] = None

    def show_event(self, event: TimelineEvent) -> None:
        """Display details for a specific event."""
        self.current_event = event
        self.current_agent = None
        self._render_event()

    def show_agent(self, agent: AgentNode) -> None:
        """Display details for a specific agent."""
        self.current_agent = agent
        self.current_event = None
        self._render_agent()

    def clear(self) -> None:
        """Clear the inspector."""
        self.current_event = None
        self.current_agent = None
        self.remove_children()

    def _render_event(self) -> None:
        """Render event details."""
        if not self.current_event:
            return

        self.remove_children()
        event = self.current_event

        # Create content
        content = Text()

        # Header
        content.append("═" * 40 + "\n", style="bold cyan")
        content.append(f"Event: {event.event_type}\n", style="bold white")
        content.append("═" * 40 + "\n\n", style="bold cyan")

        # Basic info
        content.append("Timestamp: ", style="bold")
        content.append(f"{event.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n\n")

        if event.agent_name:
            content.append("Agent: ", style="bold")
            content.append(f"{event.agent_name}\n\n")

        if event.agent_type:
            content.append("Agent Type: ", style="bold")
            content.append(f"{event.agent_type}\n\n")

        content.append("Level: ", style="bold")
        level_color = {
            "debug": "dim",
            "info": "white",
            "success": "green",
            "warning": "yellow",
            "error": "red",
        }.get(event.level, "white")
        content.append(f"{event.level}\n\n", style=level_color)

        # Event-specific details
        if event.event_type == "llm_response":
            content.append(self._render_llm_response(event.data))
        elif event.event_type == "tool_call":
            content.append(self._render_tool_call(event.data))
        elif event.event_type == "tool_result":
            content.append(self._render_tool_result(event.data))
        elif event.event_type == "execution_summary":
            content.append(self._render_execution_summary(event.data))
        elif event.event_type == "agent_action":
            content.append(self._render_agent_action(event.data))
        elif event.data:
            content.append(self._render_generic_data(event.data))

        # Add to widget
        self.mount(Static(content))

    def _render_llm_response(self, data: dict) -> Text:
        """Render LLM response details."""
        text = Text()

        # Model
        text.append("Model: ", style="bold")
        text.append(f"{data.get('model', 'unknown')}\n\n")

        # Token usage
        tokens = data.get("tokens", {})
        if isinstance(tokens, dict):
            text.append("Tokens:\n", style="bold")
            text.append(f"  Total: {tokens.get('total', 0)}\n")
            text.append(f"  Prompt: {tokens.get('prompt', 0)}\n")
            text.append(f"  Completion: {tokens.get('completion', 0)}\n\n")

        # Reasoning
        reasoning = data.get("reasoning")
        if reasoning:
            text.append("Reasoning:\n", style="bold yellow")
            text.append("─" * 40 + "\n", style="dim")
            # Truncate if too long
            if len(reasoning) > 500:
                text.append(reasoning[:500] + "...\n", style="italic")
                text.append(f"[{len(reasoning) - 500} more chars]\n", style="dim")
            else:
                text.append(reasoning + "\n", style="italic")
            text.append("─" * 40 + "\n\n", style="dim")

        # Content
        content = data.get("content")
        if content:
            text.append("Content:\n", style="bold")
            text.append("─" * 40 + "\n", style="dim")
            if len(content) > 300:
                text.append(content[:300] + "...\n")
                text.append(f"[{len(content) - 300} more chars]\n", style="dim")
            else:
                text.append(content + "\n")
            text.append("─" * 40 + "\n\n", style="dim")

        return text

    def _render_tool_call(self, data: dict) -> Text:
        """Render tool call details."""
        text = Text()

        # Tool name
        text.append("Tool: ", style="bold")
        text.append(f"{data.get('tool_name', 'unknown')}\n\n", style="cyan")

        # Tool call ID
        if "tool_call_id" in data:
            text.append("Call ID: ", style="bold")
            text.append(f"{data['tool_call_id']}\n\n", style="dim")

        # Parameters
        params = data.get("params", {})
        if params:
            text.append("Parameters:\n", style="bold")
            text.append("─" * 40 + "\n", style="dim")

            # Format as JSON
            try:
                json_str = json.dumps(params, indent=2)
                text.append(json_str + "\n")
            except:
                text.append(str(params) + "\n")

            text.append("─" * 40 + "\n\n", style="dim")

        return text

    def _render_tool_result(self, data: dict) -> Text:
        """Render tool result details."""
        text = Text()

        # Tool name
        text.append("Tool: ", style="bold")
        text.append(f"{data.get('tool_name', 'unknown')}\n\n", style="cyan")

        # Status
        is_error = data.get("is_error", False)
        text.append("Status: ", style="bold")
        if is_error:
            text.append("ERROR\n\n", style="bold red")
        else:
            text.append("SUCCESS\n\n", style="bold green")

        # Tool call ID
        if "tool_call_id" in data:
            text.append("Call ID: ", style="bold")
            text.append(f"{data['tool_call_id']}\n\n", style="dim")

        # Result
        result = data.get("result_content", "")
        if result:
            text.append("Result:\n", style="bold")
            text.append("─" * 40 + "\n", style="dim")

            # Truncate if too long
            if len(result) > 500:
                text.append(result[:500] + "...\n")
                text.append(f"[{len(result) - 500} more chars]\n", style="dim")
            else:
                text.append(result + "\n")

            text.append("─" * 40 + "\n\n", style="dim")

        return text

    def _render_execution_summary(self, data: dict) -> Text:
        """Render execution summary details."""
        text = Text()

        # Success status
        success = data.get("success", False)
        text.append("Success: ", style="bold")
        if success:
            text.append("✓ Yes\n\n", style="bold green")
        else:
            text.append("✗ No\n\n", style="bold red")

        # Iterations
        text.append("Iterations: ", style="bold")
        text.append(f"{data.get('iterations', 0)}\n\n")

        # Tokens
        text.append("Total Tokens: ", style="bold")
        text.append(f"{data.get('tokens', 0)}\n\n")

        # Termination reason
        reason = data.get("termination_reason")
        if reason:
            text.append("Termination Reason: ", style="bold")
            text.append(f"{reason}\n\n")

        return text

    def _render_agent_action(self, data: dict) -> Text:
        """Render agent action details."""
        text = Text()

        # Action
        text.append("Action: ", style="bold")
        text.append(f"{data.get('action', '')}\n\n", style="green")

        # Details
        details = data.get("details")
        if details:
            text.append("Details: ", style="bold")
            text.append(f"{details}\n\n")

        return text

    def _render_generic_data(self, data: dict) -> Text:
        """Render generic data as JSON."""
        text = Text()

        text.append("Data:\n", style="bold")
        text.append("─" * 40 + "\n", style="dim")

        try:
            json_str = json.dumps(data, indent=2)
            text.append(json_str + "\n")
        except:
            text.append(str(data) + "\n")

        text.append("─" * 40 + "\n\n", style="dim")

        return text

    def _render_agent(self) -> None:
        """Render agent details."""
        if not self.current_agent:
            return

        self.remove_children()
        agent = self.current_agent

        # Create content
        content = Text()

        # Header
        content.append("═" * 40 + "\n", style="bold cyan")
        content.append(f"Agent: {agent.name}\n", style="bold white")
        content.append("═" * 40 + "\n\n", style="bold cyan")

        # Type
        content.append("Type: ", style="bold")
        content.append(f"{agent.agent_type}\n\n")

        # State
        content.append("State: ", style="bold")
        state_colors = {
            "completed": "green",
            "failed": "red",
            "running": "yellow",
            "waiting": "cyan",
            "created": "white",
        }
        state_color = state_colors.get(agent.state.value, "white")
        content.append(f"{agent.state.value}\n\n", style=state_color)

        # Parent
        if agent.parent:
            content.append("Parent: ", style="bold")
            content.append(f"{agent.parent}\n\n")

        # Children
        if agent.children:
            content.append("Children:\n", style="bold")
            for child in agent.children:
                content.append(f"  • {child}\n")
            content.append("\n")

        # Metrics
        content.append("Metrics:\n", style="bold cyan")
        content.append(f"  Iterations: {agent.iteration_count}\n")
        content.append(f"  Tokens: {agent.total_tokens:,}\n")

        if agent.duration:
            content.append(f"  Duration: {agent.duration:.2f}s\n")

        if agent.termination_reason:
            content.append(f"  Termination: {agent.termination_reason}\n")

        content.append("\n")

        # Timestamps
        if agent.start_time:
            content.append("Start Time: ", style="bold")
            content.append(f"{agent.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

        if agent.end_time:
            content.append("End Time: ", style="bold")
            content.append(f"{agent.end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Add to widget
        self.mount(Static(content))
