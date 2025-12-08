"""Session and agent data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum


class AgentState(Enum):
    """Agent execution state."""
    CREATED = "created"
    RUNNING = "running"
    WAITING = "waiting"  # Waiting for tool result
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentNode:
    """Represents an agent in the hierarchy."""
    name: str
    agent_type: str  # ORCHESTRATOR, SUBAGENT
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    state: AgentState = AgentState.CREATED

    # Execution metrics
    iteration_count: int = 0
    total_tokens: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    termination_reason: Optional[str] = None

    # Execution details
    model: Optional[str] = None
    max_iterations: Optional[int] = None
    max_tokens: Optional[int] = None

    @property
    def duration(self) -> Optional[float]:
        """Calculate execution duration in seconds."""
        if self.start_time is None or self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()

    @property
    def is_complete(self) -> bool:
        """Check if agent has completed execution."""
        return self.state in (AgentState.COMPLETED, AgentState.FAILED)

    @property
    def success(self) -> bool:
        """Check if agent completed successfully."""
        return self.state == AgentState.COMPLETED


@dataclass
class SessionModel:
    """Complete session state."""
    session_id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Agent hierarchy
    agents: Dict[str, AgentNode] = field(default_factory=dict)
    root_agent: Optional[str] = None

    # Timeline data (imported to avoid circular dependencies)
    events: List = field(default_factory=list)  # List[TimelineEvent]
    tool_calls: List = field(default_factory=list)  # List[ToolCallSpan]
    llm_calls: List = field(default_factory=list)  # List[LLMCallMarker]

    # Metrics
    total_tokens: int = 0
    total_cycles: int = 0
    completion_reason: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        """Check if session has completed."""
        return self.end_time is not None

    @property
    def duration(self) -> Optional[float]:
        """Calculate session duration in seconds."""
        if self.start_time is None or self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()

    def get_agent(self, name: str) -> Optional[AgentNode]:
        """Get agent by name."""
        return self.agents.get(name)

    def add_agent(self, agent: AgentNode) -> None:
        """Add an agent to the session."""
        self.agents[agent.name] = agent

        # Set as root if it's the orchestrator and no root exists
        if agent.agent_type.upper() == "ORCHESTRATOR" and self.root_agent is None:
            self.root_agent = agent.name

    def get_children(self, agent_name: str) -> List[AgentNode]:
        """Get all child agents of a given agent."""
        agent = self.agents.get(agent_name)
        if agent is None:
            return []
        return [self.agents[child] for child in agent.children if child in self.agents]

    def get_agent_hierarchy(self) -> List[tuple[AgentNode, int]]:
        """Get flattened agent hierarchy with depth levels.

        Returns:
            List of (agent, depth) tuples in tree traversal order.
        """
        if self.root_agent is None:
            return []

        result = []

        def traverse(agent_name: str, depth: int):
            agent = self.agents.get(agent_name)
            if agent is None:
                return
            result.append((agent, depth))
            for child_name in agent.children:
                traverse(child_name, depth + 1)

        traverse(self.root_agent, 0)
        return result
