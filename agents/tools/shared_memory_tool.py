"""Tool for agents to interact with shared memory system."""

from typing import List, Optional, Dict, Any
from .base import Tool
from ..utils.shared_memory import get_shared_memory
from ..utils.persistent_memory import get_persistent_memory


class SharedMemoryTool(Tool):
    """Tool for storing and retrieving information from shared memory."""

    def __init__(self, agent_name: str = "unknown", task_id: str = "default"):
        super().__init__(
            name="shared_memory",
            description="Store and retrieve information from shared memory accessible to all agents. Use for coordination, handoffs, and persistent data storage.",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["store", "search", "get", "get_recent", "get_task_history", "update", "get_stats", "browse_categories", "list_by_agent"],
                        "description": "The action to perform on shared memory"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["research", "analysis", "forecast_data", "decisions", "progress", "errors", "coordination"],
                        "description": "Category of information being stored (required for store action)"
                    },
                    "title": {
                        "type": "string",
                        "description": "Brief title/summary of the information (required for store action)"
                    },
                    "content": {
                        "type": "string",
                        "description": "The main content/data to store (required for store action)"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization and search (optional for store action)"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional structured metadata (optional for store action)",
                        "additionalProperties": True
                    },
                    "entry_id": {
                        "type": "string",
                        "description": "ID of specific entry to retrieve or update (required for get/update actions)"
                    },
                    "search_category": {
                        "type": "string",
                        "description": "Category to search within (optional for search action)"
                    },
                    "search_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to search for (optional for search action)"
                    },
                    "search_content": {
                        "type": "string",
                        "description": "Text to search for in content (optional for search action)"
                    },
                    "search_agent": {
                        "type": "string",
                        "description": "Agent name to filter by (optional for search action)"
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                        "description": "Maximum number of results to return (optional for search/get_recent actions)"
                    }
                },
                "required": ["action"]
            }
        )
        self.agent_name = agent_name
        self.task_id = task_id
        self.memory = get_shared_memory()

    async def execute(self, action: str, **kwargs) -> str:
        """Execute the shared memory action."""
        try:
            if action == "store":
                return await self._store(**kwargs)
            elif action == "search":
                return await self._search(**kwargs)
            elif action == "get":
                return await self._get(**kwargs)
            elif action == "get_recent":
                return await self._get_recent(**kwargs)
            elif action == "get_task_history":
                return await self._get_task_history(**kwargs)
            elif action == "update":
                return await self._update(**kwargs)
            elif action == "get_stats":
                return await self._get_stats()
            elif action == "browse_categories":
                return await self._browse_categories(**kwargs)
            elif action == "list_by_agent":
                return await self._list_by_agent(**kwargs)
            else:
                return f"Error: Invalid action '{action}'"
        except Exception as e:
            return f"Error executing shared memory action '{action}': {e}"

    async def _store(
        self,
        category: str,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Store information in shared memory."""
        entry_id = self.memory.store(
            agent_name=self.agent_name,
            task_id=self.task_id,
            category=category,
            title=title,
            content=content,
            metadata=metadata,
            tags=tags or []
        )

        return f"✅ Stored information in shared memory:\n" \
               f"📝 ID: {entry_id}\n" \
               f"📂 Category: {category}\n" \
               f"🏷️ Title: {title}\n" \
               f"🔖 Tags: {', '.join(tags or [])}\n" \
               f"📄 Content length: {len(content)} characters\n" \
               f"🤖 Agent: {self.agent_name}\n" \
               f"📋 Task: {self.task_id}"

    async def _search(
        self,
        search_category: Optional[str] = None,
        search_tags: Optional[List[str]] = None,
        search_content: Optional[str] = None,
        search_agent: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> str:
        """Search shared memory entries."""
        results = self.memory.search(
            agent_name=search_agent,
            category=search_category,
            tags=search_tags,
            content_contains=search_content,
            limit=limit
        )

        if not results:
            return "🔍 No matching entries found in shared memory."

        formatted_results = []
        for entry in results:
            formatted_results.append(
                f"📝 ID: {entry.id}\n"
                f"🤖 Agent: {entry.agent_name}\n"
                f"📂 Category: {entry.category}\n"
                f"🏷️ Title: {entry.title}\n"
                f"🔖 Tags: {', '.join(entry.tags)}\n"
                f"⏰ Time: {entry.timestamp}\n"
                f"📄 Content: {entry.content[:200]}{'...' if len(entry.content) > 200 else ''}\n"
                f"{'─' * 50}"
            )

        return f"🔍 Found {len(results)} matching entries:\n\n" + "\n\n".join(formatted_results)

    async def _get(self, entry_id: str, **kwargs) -> str:
        """Get a specific memory entry by ID."""
        entry = self.memory.get(entry_id)
        if not entry:
            return f"❌ Entry with ID '{entry_id}' not found."

        return f"📝 Memory Entry: {entry.id}\n" \
               f"🤖 Agent: {entry.agent_name}\n" \
               f"📋 Task: {entry.task_id}\n" \
               f"📂 Category: {entry.category}\n" \
               f"🏷️ Title: {entry.title}\n" \
               f"🔖 Tags: {', '.join(entry.tags)}\n" \
               f"⏰ Timestamp: {entry.timestamp}\n" \
               f"📊 Metadata: {entry.metadata}\n" \
               f"📄 Content:\n{entry.content}"

    async def _get_recent(self, limit: int = 10, **kwargs) -> str:
        """Get recent memory entries."""
        results = self.memory.get_recent(limit=limit)
        if not results:
            return "📭 No entries found in shared memory."

        formatted_results = []
        for entry in results:
            formatted_results.append(
                f"📝 {entry.id} | {entry.agent_name} | {entry.category}\n"
                f"🏷️ {entry.title}\n"
                f"📄 {entry.content[:150]}{'...' if len(entry.content) > 150 else ''}"
            )

        return f"🕒 {len(results)} most recent entries:\n\n" + "\n\n".join(formatted_results)

    async def _get_task_history(self, **kwargs) -> str:
        """Get all entries for the current task."""
        results = self.memory.get_task_history(self.task_id)
        if not results:
            return f"📭 No entries found for task '{self.task_id}'."

        formatted_results = []
        for entry in results:
            formatted_results.append(
                f"📝 {entry.id} | {entry.agent_name} | {entry.category}\n"
                f"🏷️ {entry.title}\n"
                f"⏰ {entry.timestamp}\n"
                f"📄 {entry.content[:200]}{'...' if len(entry.content) > 200 else ''}"
            )

        return f"📋 Task '{self.task_id}' history ({len(results)} entries):\n\n" + "\n\n".join(formatted_results)

    async def _update(self, entry_id: str, **updates) -> str:
        """Update an existing memory entry."""
        success = self.memory.update(entry_id, **updates)
        if not success:
            return f"❌ Failed to update entry '{entry_id}' (not found)."

        return f"✅ Updated entry '{entry_id}' with changes: {list(updates.keys())}"

    async def _get_stats(self, **kwargs) -> str:
        """Get memory usage statistics."""
        stats = self.memory.get_stats()

        category_breakdown = "\n".join(
            f"  📂 {cat}: {count}" for cat, count in stats["categories"].items()
        )

        agent_breakdown = "\n".join(
            f"  🤖 {agent}: {count}" for agent, count in stats["agents"].items()
        )

        return f"📊 Shared Memory Statistics:\n\n" \
               f"📝 Total Entries: {stats['total_entries']}\n" \
               f"💾 Estimated Size: {stats['estimated_size_bytes']:,} bytes\n" \
               f"📁 Storage Location: {stats['memory_dir']}\n\n" \
               f"📂 By Category:\n{category_breakdown}\n\n" \
               f"🤖 By Agent:\n{agent_breakdown}"

    async def _browse_categories(self, **kwargs) -> str:
        """Browse available content by category with preview."""
        all_results = self.memory.search(limit=None)
        if not all_results:
            return "📭 No entries found in shared memory."

        # Group by category
        by_category = {}
        for entry in all_results:
            if entry.category not in by_category:
                by_category[entry.category] = []
            by_category[entry.category].append(entry)

        category_summaries = []
        for category, entries in by_category.items():
            recent_titles = [e.title for e in sorted(entries, key=lambda x: x.timestamp, reverse=True)[:3]]
            category_summaries.append(
                f"📂 **{category.upper()}** ({len(entries)} entries)\n"
                f"   Recent: {', '.join(recent_titles[:2])}{'...' if len(recent_titles) > 2 else ''}"
            )

        return f"🗂️ **Memory Categories Overview:**\n\n" + "\n\n".join(category_summaries) + \
               f"\n\n💡 Use `search` with `search_category` to explore specific categories."

    async def _list_by_agent(self, **kwargs) -> str:
        """List recent work by each agent for easy discovery."""
        all_results = self.memory.search(limit=None)
        if not all_results:
            return "📭 No entries found in shared memory."

        # Group by agent
        by_agent = {}
        for entry in all_results:
            if entry.agent_name not in by_agent:
                by_agent[entry.agent_name] = []
            by_agent[entry.agent_name].append(entry)

        agent_summaries = []
        for agent_name, entries in by_agent.items():
            sorted_entries = sorted(entries, key=lambda x: x.timestamp, reverse=True)[:3]
            entry_previews = []
            for entry in sorted_entries:
                entry_previews.append(f"   • {entry.category}: {entry.title}")

            agent_summaries.append(
                f"🤖 **{agent_name}** ({len(entries)} contributions)\n" +
                "\n".join(entry_previews)
            )

        return f"👥 **Work by Agent:**\n\n" + "\n\n".join(agent_summaries) + \
               f"\n\n💡 Use `search` with `search_agent` to see specific agent's work."


class SharedMemoryManagerTool(Tool):
    """Administrative tool for managing shared memory (coordinator use)."""

    def __init__(self):
        super().__init__(
            name="memory_manager",
            description="Administrative functions for managing shared memory system. For coordinator use.",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["export_task", "clear_task", "get_task_summary"],
                        "description": "Administrative action to perform"
                    },
                    "target_task_id": {
                        "type": "string",
                        "description": "Task ID to target (required for most actions)"
                    },
                    "output_file": {
                        "type": "string",
                        "description": "Output file path (required for export_task action)"
                    },
                },
                "required": ["action"]
            }
        )
        self.memory = get_shared_memory()

    async def execute(self, action: str, **kwargs) -> str:
        """Execute administrative action."""
        try:
            if action == "export_task":
                return await self._export_task(**kwargs)
            elif action == "clear_task":
                return await self._clear_task(**kwargs)
            elif action == "get_task_summary":
                return await self._get_task_summary(**kwargs)
            else:
                return f"Error: Invalid action '{action}'"
        except Exception as e:
            return f"Error executing memory manager action '{action}': {e}"

    async def _export_task(self, target_task_id: str, output_file: str, **kwargs) -> str:
        """Export all entries for a task to a file."""
        success = self.memory.export_task(target_task_id, output_file)
        if success:
            return f"✅ Exported task '{target_task_id}' to '{output_file}'"
        else:
            return f"❌ Failed to export task '{target_task_id}' (no entries found or file error)"

    async def _get_task_summary(self, target_task_id: str, **kwargs) -> str:
        """Get a summary of all work done for a task."""
        entries = self.memory.get_task_history(target_task_id)
        if not entries:
            return f"📭 No entries found for task '{target_task_id}'"

        # Group by category and agent
        by_category = {}
        by_agent = {}
        total_content_length = 0

        for entry in entries:
            by_category[entry.category] = by_category.get(entry.category, 0) + 1
            by_agent[entry.agent_name] = by_agent.get(entry.agent_name, 0) + 1
            total_content_length += len(entry.content)

        category_summary = "\n".join(f"  📂 {cat}: {count}" for cat, count in by_category.items())
        agent_summary = "\n".join(f"  🤖 {agent}: {count}" for agent, count in by_agent.items())

        return f"📋 Task Summary: {target_task_id}\n" \
               f"{'═' * 50}\n" \
               f"📝 Total Entries: {len(entries)}\n" \
               f"💾 Total Content: {total_content_length:,} characters\n" \
               f"⏰ Time Range: {entries[-1].timestamp} → {entries[0].timestamp}\n\n" \
               f"📂 By Category:\n{category_summary}\n\n" \
               f"🤖 By Agent:\n{agent_summary}"

    async def _clear_task(self, target_task_id: str, **kwargs) -> str:
        """Clear all entries for a specific task."""
        entries = self.memory.get_task_history(target_task_id)
        if not entries:
            return f"📭 No entries found for task '{target_task_id}'"

        deleted_count = 0
        for entry in entries:
            if self.memory.delete(entry.id):
                deleted_count += 1

        return f"🗑️ Deleted {deleted_count}/{len(entries)} entries for task '{target_task_id}'"

    async def _cleanup_old(self, days_old: int = 30, **kwargs) -> str:
        """Clean up entries older than specified days."""
        # This would require datetime comparison logic
        return f"🧹 Cleanup functionality not yet implemented for {days_old} days threshold"

class PersistentMemoryTool(Tool):
    """Tool for storing and retrieving information from persistent memory."""

    def __init__(self):
        super().__init__(
            name="persistent_memory",
            description="Store and retrieve information from persistent memory.",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["store", "search", "get"],
                        "description": "The action to perform on persistent memory."
                    },
                    "category": {
                        "type": "string",
                        "description": "Category of information being stored (required for store action)"
                    },
                    "title": {
                        "type": "string",
                        "description": "Brief title/summary of the information (required for store action)"
                    },
                    "content": {
                        "type": "string",
                        "description": "The main content/data to store (required for store action)"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization and search (optional for store action)"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional structured metadata (optional for store action)",
                        "additionalProperties": True
                    },
                    "entry_id": {
                        "type": "string",
                        "description": "ID of specific entry to retrieve or update (required for get action)"
                    },

                    "search_category": {
                        "type": "string",
                        "description": "Category to search within (optional for search action)"
                    },
                    "search_tags": {
                        "type": "array",

                        "items": {"type": "string"},
                        "description": "Tags to search for (optional for search action)"
                    },
                    "search_content": {
                        "type": "string",
                        "description": "Text to search for in content (optional for search action)"
                    },
                },
            "required": ["action"]
            }
        )
        self.persistent_memory = get_persistent_memory()

    async def execute(self, action: str, **kwargs) -> str:
        """Execute the persistent memory action."""
        try:
            if action == "store":
                return await self._store(**kwargs)
            elif action == "search":
                return await self._search(**kwargs)
            elif action == "get":
                return await self._get(**kwargs)
            else:
                return f"Error: Invalid action '{action}'"
        except Exception as e:
            return f"Error executing persistent memory action '{action}': {e}"
    
    async def _store(self, **kwargs) -> str:
        """Store information in persistent memory."""
        

    async def _search(self, **kwargs) -> str:
        """Search persistent memory."""
        results = self.persistent_memory.search(
            category=kwargs.get("search_category"),
            tags=kwargs.get("search_tags"),
            content_contains=kwargs.get("search_content"),
            limit=kwargs.get("limit")
        )
        
        if not results:
            return "🔍 No matching entries found in persistent memory."
        
        formatted_results = []
        for entry in results:
            formatted_results.append(
                f"📝 ID: {entry.id}\n"
                f"🤖 Agent: {entry.agent_name}\n"
                f"📂 Category: {entry.category}\n"
                f"🏷️ Title: {entry.title}\n"
                f"🔖 Tags: {', '.join(entry.tags)}\n"
                f"⏰ Time: {entry.timestamp}\n"
                f"📄 Content: {entry.content[:200]}{'...' if len(entry.content) > 200 else ''}\n"
                f"{'─' * 50}"
            )
        
        return f"🔍 Found {len(results)} matching entries:\n\n" + "\n\n".join(formatted_results)

    async def _get(self, **kwargs) -> str:
        """Get a specific entry from persistent memory."""
        entry = self.persistent_memory.get(kwargs.get("entry_id"))
        if not entry:
            return f"❌ Entry with ID '{kwargs.get('entry_id')}' not found."
        
        return f"📝 Memory Entry: {entry.id}\n" \
               f"🤖 Agent: {entry.agent_name}\n" \
               f"📂 Category: {entry.category}\n" \
               f"🏷️ Title: {entry.title}\n" \
               f"🔖 Tags: {', '.join(entry.tags)}\n" \
               f"⏰ Timestamp: {entry.timestamp}\n" \
               f"📊 Metadata: {entry.metadata}\n" \
               f"📄 Content:\n{entry.content}"
