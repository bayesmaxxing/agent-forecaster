"""Tool for agents to interact with persistent memory system."""

from typing import List, Optional, Dict, Any
from .base import Tool
from ..utils.persistent_memory import get_persistent_memory


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
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent storing the information (optional, defaults to 'unknown')"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task this memory relates to (optional, defaults to 'default')"
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
        category = kwargs.get("category")
        title = kwargs.get("title")
        content = kwargs.get("content")
        
        if not category or not title or not content:
            return "❌ Error: 'category', 'title', and 'content' are required for store action."
        
        entry_id = self.persistent_memory.store(
            agent_name=kwargs.get("agent_name", "unknown"),
            task_id=kwargs.get("task_id", "default"),
            category=category,
            title=title,
            content=content,
            metadata=kwargs.get("metadata", {}),
            tags=kwargs.get("tags", [])
        )
        
        return f"✅ Successfully stored persistent memory entry with ID: {entry_id}\n" \
               f"📂 Category: {category}\n" \
               f"🏷️ Title: {title}\n" \
               f"📄 Content length: {len(content)} characters"

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

