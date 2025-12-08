"""Agent tree widget for displaying agent hierarchy."""

from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from ..models.session import SessionModel, AgentNode, AgentState


class AgentTreeWidget(Tree):
    """Tree widget for displaying agent hierarchy."""

    def __init__(self, *args, **kwargs):
        super().__init__("Agents", *args, **kwargs)
        self.session: SessionModel | None = None
        self.agent_nodes: dict[str, TreeNode] = {}

    def update_from_session(self, session: SessionModel) -> None:
        """Update the tree from session data."""
        self.session = session
        self.rebuild_tree()

    def rebuild_tree(self) -> None:
        """Rebuild the entire tree from session data."""
        if not self.session:
            return

        # Clear existing tree
        self.clear()
        self.agent_nodes.clear()

        # Set root label
        root = self.root
        root.set_label(f"Session: {self.session.session_id}")
        root.expand()

        # Build tree from hierarchy
        if self.session.root_agent:
            self._add_agent_subtree(root, self.session.root_agent)

    def _add_agent_subtree(self, parent_node: TreeNode, agent_name: str) -> None:
        """Recursively add agent and its children to the tree."""
        agent = self.session.agents.get(agent_name)
        if not agent:
            return

        # Create label with status indicator
        status_icon = self._get_status_icon(agent)
        label = f"{status_icon} {agent.name}"

        # Add metrics
        if agent.iteration_count > 0 or agent.total_tokens > 0:
            metrics = []
            if agent.iteration_count > 0:
                metrics.append(f"iter:{agent.iteration_count}")
            if agent.total_tokens > 0:
                if agent.total_tokens >= 1000:
                    metrics.append(f"{agent.total_tokens / 1000:.1f}k tok")
                else:
                    metrics.append(f"{agent.total_tokens} tok")
            label += f" ({', '.join(metrics)})"

        # Add node to tree
        node = parent_node.add(label, data=agent)
        self.agent_nodes[agent_name] = node

        # Auto-expand if agent has children
        if agent.children:
            node.expand()

        # Add children
        for child_name in agent.children:
            self._add_agent_subtree(node, child_name)

    def _get_status_icon(self, agent: AgentNode) -> str:
        """Get status icon for agent."""
        if agent.state == AgentState.COMPLETED:
            return "✓"
        elif agent.state == AgentState.FAILED:
            return "✗"
        elif agent.state == AgentState.RUNNING:
            return "⟳"
        elif agent.state == AgentState.WAITING:
            return "⋯"
        else:  # CREATED
            return "○"

    def get_selected_agent(self) -> AgentNode | None:
        """Get the currently selected agent."""
        if not self.cursor_node or not self.cursor_node.data:
            return None
        return self.cursor_node.data

    def select_agent(self, agent_name: str) -> None:
        """Select a specific agent by name."""
        node = self.agent_nodes.get(agent_name)
        if node:
            self.select_node(node)
