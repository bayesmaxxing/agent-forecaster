"""Builders for constructing session state from event streams."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict
from .session import SessionModel, AgentNode, AgentState
from .events import TimelineEvent, ToolCallSpan, LLMCallMarker


class AgentTreeBuilder:
    """Builds agent hierarchy from event stream."""

    def __init__(self):
        self.session = SessionModel(session_id="unknown")
        self.current_parent: Optional[str] = None  # Track current parent for subagent creation
        self.pending_tool_calls: Dict[str, ToolCallSpan] = {}  # tool_call_id -> ToolCallSpan
        self.pending_tool_calls_queue: Dict[str, List[ToolCallSpan]] = defaultdict(list)  # (agent, tool) -> list of spans

    def process_event(self, event_data: Dict[str, Any]) -> None:
        """Process a single JSONL log entry and update session state."""
        event = TimelineEvent.from_json_entry(event_data)
        self.session.events.append(event)

        event_type = event.event_type
        agent_name = event.agent_name

        # Dispatch to specific handlers
        if event_type == "session_start":
            self._handle_session_start(event)
        elif event_type == "session_end":
            self._handle_session_end(event)
        elif event_type == "agent_action":
            self._handle_agent_action(event)
        elif event_type == "subagent_lifecycle":
            self._handle_subagent_lifecycle(event)
        elif event_type == "tool_call":
            self._handle_tool_call(event)
        elif event_type == "tool_result":
            self._handle_tool_result(event)
        elif event_type == "llm_response":
            self._handle_llm_response(event)
        elif event_type == "execution_summary":
            self._handle_execution_summary(event)
        elif event_type == "cycle":
            self._handle_cycle(event)

    def _handle_session_start(self, event: TimelineEvent) -> None:
        """Handle session start event."""
        if self.session.start_time is None:
            self.session.start_time = event.timestamp
        # Update session_id from top-level field
        if event.session_id:
            self.session.session_id = event.session_id

    def _handle_session_end(self, event: TimelineEvent) -> None:
        """Handle session end event."""
        self.session.end_time = event.timestamp
        self.session.completion_reason = event.data.get("reason")

    def _handle_agent_action(self, event: TimelineEvent) -> None:
        """Handle agent action event."""
        agent_name = event.agent_name
        if not agent_name:
            return

        agent_type = event.agent_type or "unknown"

        # Create agent if it doesn't exist
        if agent_name not in self.session.agents:
            agent = AgentNode(
                name=agent_name,
                agent_type=agent_type,
                start_time=event.timestamp,
            )
            self.session.add_agent(agent)

        # Update agent state based on action
        agent = self.session.agents[agent_name]
        action = event.data.get("action", "")

        if "initialized" in action.lower() or "starting" in action.lower():
            agent.state = AgentState.RUNNING
            if agent.start_time is None:
                agent.start_time = event.timestamp
        elif "completed" in action.lower():
            agent.state = AgentState.COMPLETED
            agent.end_time = event.timestamp
        elif "failed" in action.lower():
            agent.state = AgentState.FAILED
            agent.end_time = event.timestamp

        # Track current agent for parent-child relationships
        if agent_type.upper() == "ORCHESTRATOR":
            self.current_parent = agent_name

    def _handle_subagent_lifecycle(self, event: TimelineEvent) -> None:
        """Handle subagent lifecycle event."""
        agent_name = event.agent_name
        if not agent_name:
            return

        action = event.data.get("action", "")

        if action == "Created":
            # Create new subagent
            if agent_name not in self.session.agents:
                agent = AgentNode(
                    name=agent_name,
                    agent_type="SUBAGENT",
                    parent=self.current_parent,
                    start_time=event.timestamp,
                    state=AgentState.CREATED,
                )
                self.session.add_agent(agent)

                # Add to parent's children
                if self.current_parent and self.current_parent in self.session.agents:
                    parent = self.session.agents[self.current_parent]
                    if agent_name not in parent.children:
                        parent.children.append(agent_name)

        elif action == "Started":
            agent = self.session.agents.get(agent_name)
            if agent:
                agent.state = AgentState.RUNNING
                if agent.start_time is None:
                    agent.start_time = event.timestamp

        elif action == "Completed":
            agent = self.session.agents.get(agent_name)
            if agent:
                agent.state = AgentState.COMPLETED
                agent.end_time = event.timestamp

    def _handle_tool_call(self, event: TimelineEvent) -> None:
        """Handle tool call event."""
        agent_name = event.agent_name
        if not agent_name:
            return

        tool_name = event.data.get("tool_name", "unknown")
        tool_call_id = event.data.get("tool_call_id")
        params = event.data.get("params", {})

        # Create tool call span
        span = ToolCallSpan(
            tool_name=tool_name,
            agent_name=agent_name,
            start_time=event.timestamp,
            params=params,
            tool_call_id=tool_call_id,
        )

        # Track pending tool calls using both strategies:
        # 1. By tool_call_id (if available)
        if tool_call_id:
            self.pending_tool_calls[tool_call_id] = span

        # 2. By agent+tool queue (for FIFO matching when no ID)
        queue_key = f"{agent_name}:{tool_name}"
        self.pending_tool_calls_queue[queue_key].append(span)

        # Track which agent is making the call
        if tool_name in ("subagent_manager", "SubagentManagerTool"):
            # This agent will be parent of next subagent
            self.current_parent = agent_name

        # Update agent state
        agent = self.session.agents.get(agent_name)
        if agent:
            agent.state = AgentState.WAITING

    def _handle_tool_result(self, event: TimelineEvent) -> None:
        """Handle tool result event."""
        agent_name = event.agent_name
        tool_call_id = event.data.get("tool_call_id")
        tool_name = event.data.get("tool_name", "unknown")
        result_content = event.data.get("result_content", "")
        is_error = event.data.get("is_error", False)

        span = None

        # Try to match by tool_call_id first (if available)
        if tool_call_id and tool_call_id in self.pending_tool_calls:
            span = self.pending_tool_calls[tool_call_id]
            del self.pending_tool_calls[tool_call_id]

        # If no match by ID, try FIFO matching by agent+tool
        if not span and agent_name:
            queue_key = f"{agent_name}:{tool_name}"
            if queue_key in self.pending_tool_calls_queue and self.pending_tool_calls_queue[queue_key]:
                span = self.pending_tool_calls_queue[queue_key].pop(0)
                # Also remove from pending_tool_calls if it was there
                if span.tool_call_id and span.tool_call_id in self.pending_tool_calls:
                    del self.pending_tool_calls[span.tool_call_id]

        # Complete the tool call span
        if span:
            span.end_time = event.timestamp
            span.result = result_content
            span.is_error = is_error
            # Move to completed list
            self.session.tool_calls.append(span)

        # Update agent state back to running
        agent = self.session.agents.get(agent_name)
        if agent and agent.state == AgentState.WAITING:
            agent.state = AgentState.RUNNING

    def _handle_llm_response(self, event: TimelineEvent) -> None:
        """Handle LLM response event."""
        llm_marker = LLMCallMarker.from_event(event)
        if llm_marker:
            self.session.llm_calls.append(llm_marker)

        # Update agent token count
        if event.agent_name:
            agent = self.session.agents.get(event.agent_name)
            if agent:
                tokens_data = event.data.get("tokens", {})
                if isinstance(tokens_data, dict):
                    total_tokens = tokens_data.get("total", 0)
                    if total_tokens:
                        agent.total_tokens += total_tokens
                        self.session.total_tokens += total_tokens

    def _handle_execution_summary(self, event: TimelineEvent) -> None:
        """Handle execution summary event."""
        agent_name = event.agent_name
        if not agent_name:
            return

        agent = self.session.agents.get(agent_name)
        if not agent:
            return

        # Update agent metrics
        agent.iteration_count = event.data.get("iterations", 0)
        agent.total_tokens = event.data.get("tokens", 0)
        agent.termination_reason = event.data.get("termination_reason")

        # Update state based on success
        success = event.data.get("success", False)
        agent.state = AgentState.COMPLETED if success else AgentState.FAILED

        if agent.end_time is None:
            agent.end_time = event.timestamp

    def _handle_cycle(self, event: TimelineEvent) -> None:
        """Handle cycle event."""
        cycle_number = event.data.get("cycle_number", 0)
        self.session.total_cycles = max(self.session.total_cycles, cycle_number)

    def build(self) -> SessionModel:
        """Return the built session model."""
        # Close any pending tool calls (still running)
        for span in self.pending_tool_calls.values():
            self.session.tool_calls.append(span)
        self.pending_tool_calls.clear()

        return self.session


class TimelineBuilder:
    """Builds timeline visualization data from session model."""

    def __init__(self, session: SessionModel):
        self.session = session
        self.tracks: Dict[str, int] = {}  # agent_name -> track_index

    def assign_tracks(self) -> Dict[str, int]:
        """Assign timeline track indices to agents based on hierarchy.

        Returns:
            Dictionary mapping agent names to track indices.
        """
        hierarchy = self.session.get_agent_hierarchy()

        for idx, (agent, depth) in enumerate(hierarchy):
            self.tracks[agent.name] = idx

        return self.tracks

    def get_agent_spans(self) -> List[tuple[AgentNode, int]]:
        """Get agent execution spans with track indices.

        Returns:
            List of (agent, track_index) tuples.
        """
        spans = []
        for agent_name, track_idx in self.tracks.items():
            agent = self.session.agents.get(agent_name)
            if agent:
                spans.append((agent, track_idx))
        return spans

    def get_tool_call_spans(self) -> List[tuple[ToolCallSpan, int]]:
        """Get tool call spans with track indices.

        Returns:
            List of (tool_span, track_index) tuples.
        """
        spans = []
        for tool_span in self.session.tool_calls:
            track_idx = self.tracks.get(tool_span.agent_name, 0)
            spans.append((tool_span, track_idx))
        return spans

    def get_llm_markers(self) -> List[tuple[LLMCallMarker, int]]:
        """Get LLM call markers with track indices.

        Returns:
            List of (llm_marker, track_index) tuples.
        """
        markers = []
        for llm_marker in self.session.llm_calls:
            track_idx = self.tracks.get(llm_marker.agent_name, 0)
            markers.append((llm_marker, track_idx))
        return markers
