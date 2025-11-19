"""Agent implementation with OpenAI SDK and tools."""

import asyncio
import os
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any
import logging
from datetime import datetime

from openai import OpenAI

from .tools.base import Tool
from .utils.history_util import MessageHistory
from .utils.tool_util import execute_tools
from .utils.logging_util import get_session_logger, AgentType, LogLevel

@dataclass
class SubagentConfig:
    """Configuration settings for Subagent with execution limits."""

    model: str = "grok/grok-4-fast:free"
    max_tokens: int = 8192
    temperature: float = 1.0
    context_window_tokens: int = 80000
    max_iterations: int = 10  # Maximum tool call iterations
    max_total_tokens: int = 50000  # Maximum total token usage
    termination_tools: list[str] | None = None  # Tools that end execution when called
    require_termination_tool: bool = False  # Whether termination tool must be called
    agent_id: str = "subagent"


# Logging is now handled by the centralized session logger
class Subagent:
    """OpenRouter-powered agent with tool use capabilities."""

    def __init__(
        self,
        name: str,
        system: str,
        tools: list[Tool] | None = None,
        config: SubagentConfig | None = None,
        verbose: bool = False,
        client: OpenAI | None = None,
        agent_id: str = "subagent",
    ):
        self.name = name
        self.system = system
        self.verbose = verbose
        self.tools = list(tools or [])
        self.config = config or SubagentConfig()
        self.agent_id = agent_id
        self.client = client or OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", "")
        )
        self.history = MessageHistory(
            model=self.config.model,
            system=self.system,
            context_window_tokens=self.config.context_window_tokens,
            client=self.client,
        )

        if self.verbose:
            session_logger = get_session_logger()
            session_logger.log_subagent_lifecycle(
                subagent_name=self.name,
                action="Created"
            )

        # Execution tracking
        self.iteration_count = 0
        self.total_tokens_used = 0
        self.termination_reason = None
        self.completed_successfully = False

    def _prepare_api_params(self) -> dict[str, Any]:
        """Prepare parameters for OpenAI API call."""
        messages = self.history.format_for_api()
        # Add system message at the beginning if not already present
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": self.system})
        
        params = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": messages,
        }
        
        if self.config.model == "openai/gpt-5":
            params["reasoning_effort"] = "high"
        if self.tools:
            params["tools"] = [tool.to_dict() for tool in self.tools]
        
        return params

    def _should_terminate(self, tool_calls: list | None = None) -> tuple[bool, str]:
        """Check if subagent should terminate based on configured limits."""

        # Check iteration limit
        if self.iteration_count >= self.config.max_iterations:
            return True, f"max_iterations_reached ({self.config.max_iterations})"

        # Check token limit
        if self.total_tokens_used >= self.config.max_total_tokens:
            return True, f"max_tokens_reached ({self.total_tokens_used}/{self.config.max_total_tokens})"

        # Check for termination tools
        if tool_calls and self.config.termination_tools:
            called_tools = [tc.function.name for tc in tool_calls]
            for termination_tool in self.config.termination_tools:
                if termination_tool in called_tools:
                    return True, f"termination_tool_called ({termination_tool})"

        return False, ""

    async def _agent_loop(self, user_input: str) -> dict[str, Any]:
        """Process user input and handle tool calls in a loop with termination conditions."""
        if self.verbose:
            session_logger = get_session_logger()
            session_logger.log_agent_action(
                agent_name=self.name,
                action="Received task",
                agent_type=AgentType.SUBAGENT,
                details=user_input[:100] + "..." if len(user_input) > 100 else user_input
            )
        await self.history.add_message("user", user_input)

        tool_dict = {tool.name: tool for tool in self.tools}

        while True:
            # Check termination before each iteration
            should_terminate, reason = self._should_terminate()
            if should_terminate:
                self.termination_reason = reason
                if self.verbose:
                    session_logger = get_session_logger()
                    session_logger.log_agent_action(
                        agent_name=self.name,
                        action=f"Terminating: {reason}",
                        agent_type=AgentType.SUBAGENT,
                        level=LogLevel.WARNING,
                    )
                break

            self.history.compact()
            params = self._prepare_api_params()

            response = self.client.chat.completions.create(**params)

            # Track token usage
            if response.usage:
                self.total_tokens_used += response.usage.total_tokens

            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            # Extract reasoning_details if present
            reasoning_details = None
            if hasattr(message, 'reasoning_details') and message.reasoning_details:
                reasoning_details = message.reasoning_details

            if self.verbose:
                session_logger = get_session_logger()

                # Log the full LLM response
                session_logger.log_llm_response(
                    agent_name=self.name,
                    content=message.content,
                    reasoning=reasoning_details,
                    model=response.model if hasattr(response, 'model') else self.config.model,
                    tokens=response.usage.total_tokens if response.usage else None,
                )

                # Log tool calls
                for tool_call in tool_calls:
                    import json
                    try:
                        params_dict = json.loads(tool_call.function.arguments)
                    except:
                        params_dict = {"raw": tool_call.function.arguments}

                    session_logger.log_tool_call(
                        agent_name=self.name,
                        tool_name=tool_call.function.name,
                        params=params_dict,
                    )

            await self.history.add_message(
                "assistant", message, reasoning_details, response.usage
            )

            # Check for termination tools before executing
            should_terminate, reason = self._should_terminate(tool_calls)
            if should_terminate:
                self.termination_reason = reason
                self.completed_successfully = reason.startswith("termination_tool_called")
                if self.verbose:
                    session_logger = get_session_logger()
                    level = LogLevel.SUCCESS if self.completed_successfully else LogLevel.WARNING
                    session_logger.log_agent_action(
                        agent_name=self.name,
                        action=f"Terminating: {reason}",
                        agent_type=AgentType.SUBAGENT,
                        level=level
                    )

                # Still execute the termination tool call
                if tool_calls:
                    tool_results = await execute_tools(tool_calls, tool_dict)

                    if self.verbose:
                        session_logger = get_session_logger()
                        for i, block in enumerate(tool_results):
                            content = block.get('content', '')
                            is_error = block.get('is_error', False)
                            tool_call_id = block.get('tool_call_id', '')
                            tool_name = tool_calls[i].function.name if i < len(tool_calls) else "unknown"

                            session_logger.log_tool_result(
                                agent_name=self.name,
                                tool_name=tool_name,
                                result_content=content,
                                is_error=is_error,
                                tool_call_id=tool_call_id
                            )

                    await self.history.add_message("user", tool_results)
                break

            if tool_calls:
                self.iteration_count += 1
                tool_results = await execute_tools(tool_calls, tool_dict)

                if self.verbose:
                    session_logger = get_session_logger()
                    for i, block in enumerate(tool_results):
                        content = block.get('content', '')
                        is_error = block.get('is_error', False)
                        tool_call_id = block.get('tool_call_id', '')
                        tool_name = tool_calls[i].function.name if i < len(tool_calls) else "unknown"

                        session_logger.log_tool_result(
                            agent_name=self.name,
                            tool_name=tool_name,
                            result_content=content,
                            is_error=is_error,
                            tool_call_id=tool_call_id
                        )

                await self.history.add_message("user", tool_results)
            else:
                # No tool calls means natural completion
                self.completed_successfully = True
                self.termination_reason = "natural_completion"
                break

        # Extract only serializable parts from the message
        final_message_data = {
            "content": message.content,
            "role": "assistant"
        }
        if message.tool_calls:
            final_message_data["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        
        return {
            "final_message": final_message_data,
            "termination_reason": self.termination_reason,
            "completed_successfully": self.completed_successfully,
            "iteration_count": self.iteration_count,
            "total_tokens_used": self.total_tokens_used
        }

    async def run_async(self, user_input: str) -> dict[str, Any]:
        """Run subagent with execution limits and termination conditions."""
        # Reset execution state
        self.iteration_count = 0
        self.total_tokens_used = 0
        self.termination_reason = None
        self.completed_successfully = False

        async with AsyncExitStack() as stack:
            original_tools = list(self.tools)

            try:
                result = await self._agent_loop(user_input)

                # Check if termination tool was required but not called
                if (self.config.require_termination_tool and
                    self.config.termination_tools and
                    not self.completed_successfully and
                    not self.termination_reason.startswith("termination_tool_called")):
                    result["completed_successfully"] = False
                    result["termination_reason"] += " (termination_tool_required_but_not_called)"

                if self.verbose:
                    session_logger = get_session_logger()
                    session_logger.log_execution_summary(
                        agent_name=self.name,
                        iterations=result['iteration_count'],
                        tokens=result['total_tokens_used'],
                        success=result['completed_successfully'],
                        termination_reason=result['termination_reason']
                    )

                return result
            finally:
                self.tools = original_tools

    def run(self, user_input: str) -> dict[str, Any]:
        """Run subagent synchronously with execution limits."""
        return asyncio.run(self.run_async(user_input))

    def get_execution_status(self) -> dict[str, Any]:
        """Get current execution status."""
        return {
            "iteration_count": self.iteration_count,
            "total_tokens_used": self.total_tokens_used,
            "termination_reason": self.termination_reason,
            "completed_successfully": self.completed_successfully,
            "max_iterations": self.config.max_iterations,
            "max_total_tokens": self.config.max_total_tokens,
            "termination_tools": self.config.termination_tools,
            "require_termination_tool": self.config.require_termination_tool
        }

if __name__ == "__main__":
    agent = Subagent(
        name="TestSubagent",
        system="You are a test agent.",
        tools=[],
        config=SubagentConfig(),
        verbose=True
    )

    response = agent.run("What is the weather in Tokyo?")
    # Response logged via new system