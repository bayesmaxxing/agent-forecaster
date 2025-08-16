"""Tool execution utility with parallel execution support."""

import asyncio
from typing import Any


async def _execute_single_tool(
    call: Any, tool_dict: dict[str, Any]
) -> dict[str, Any]:
    """Execute a single tool and handle errors."""
    # Handle OpenAI tool call format
    tool_call_id = call.id
    tool_name = call.function.name
    
    # Parse arguments (they come as a JSON string)
    import json
    try:
        tool_args = json.loads(call.function.arguments)
    except json.JSONDecodeError:
        tool_args = {}
    
    response = {
        "tool_call_id": tool_call_id,
        "role": "tool"
    }

    try:
        # Execute the tool directly
        result = await tool_dict[tool_name].execute(**tool_args)
        
        # Convert to string for API
        str_result = str(result)
        response["content"] = str_result
    except KeyError:
        response["content"] = f"Tool '{tool_name}' not found"
        response["is_error"] = True
    except Exception as e:
        response["content"] = f"Error executing tool: {str(e)}"
        response["is_error"] = True

    return response


async def execute_tools(
    tool_calls: list[Any], tool_dict: dict[str, Any], parallel: bool = True
) -> list[dict[str, Any]]:
    """Execute multiple tools sequentially or in parallel."""

    if parallel:
        return await asyncio.gather(
            *[_execute_single_tool(call, tool_dict) for call in tool_calls]
        )
    else:
        return [
            await _execute_single_tool(call, tool_dict) for call in tool_calls
        ]
