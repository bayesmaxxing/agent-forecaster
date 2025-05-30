"""Tools that interface with MCP servers."""

import json
from typing import Any
from .base import Tool


class MCPTool(Tool):
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        connection: "MCPConnection",
    ):
        super().__init__(
            name=name, description=description, input_schema=input_schema
        )
        self.connection = connection

    async def execute(self, **kwargs) -> str:
        """Execute the MCP tool with the given input_schema.
        Note: Currently only supports text results from MCP tools."""
        try:
            result = await self.connection.call_tool(
                self.name, arguments=kwargs
            )

            if hasattr(result, "content") and result.content:
                # Collect all text content items and combine them
                text_contents = []
                for item in result.content:
                    if getattr(item, "type", None) == "text":
                        text_contents.append(item.text)
                
                if text_contents:
                    # If we have multiple text items, combine them as a JSON array
                    if len(text_contents) > 1:
                        # Parse each JSON object and combine into an array
                        try:
                            parsed_items = [json.loads(text) for text in text_contents]
                            return json.dumps(parsed_items, indent=2, ensure_ascii=False)
                        except json.JSONDecodeError:
                            # If not JSON, just join with newlines
                            return "\n\n".join(text_contents)
                    else:
                        # Single item, return as-is
                        return text_contents[0]

            return "No text content in tool response"
        except Exception as e:
            return f"Error executing {self.name}: {e}"
