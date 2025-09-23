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
from .utils.connections import setup_mcp_connections

@dataclass
class SubagentConfig:
    """Configuration settings for Subagent with execution limits."""

    model: str = "openai/gpt-5"
    max_tokens: int = 8192
    temperature: float = 1.0
    context_window_tokens: int = 80000
    max_iterations: int = 10  # Maximum tool call iterations
    max_total_tokens: int = 50000  # Maximum total token usage
    termination_tools: list[str] | None = None  # Tools that end execution when called
    require_termination_tool: bool = False  # Whether termination tool must be called


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
    ):
        self.name = name
        self.system = system
        self.verbose = verbose
        self.tools = list(tools or [])
        self.config = config or SubagentConfig()
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
            print(f"\n[{self.name}] Subagent initialized")

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
            print(f"\n[{self.name}] Received: {user_input}")
        await self.history.add_message("user", user_input, None)

        tool_dict = {tool.name: tool for tool in self.tools}

        while True:
            # Check termination before each iteration
            should_terminate, reason = self._should_terminate()
            if should_terminate:
                self.termination_reason = reason
                if self.verbose:
                    print(f"[{self.name}] Terminating: {reason}")
                break

            self.history.truncate()
            params = self._prepare_api_params()

            response = self.client.chat.completions.create(**params)

            # Track token usage
            if response.usage:
                self.total_tokens_used += response.usage.total_tokens

            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            if self.verbose and tool_calls:
                print(f"[{self.name}] Tool calls: {[tc.function.name for tc in tool_calls]}")

            await self.history.add_message(
                "assistant", message, response.usage
            )

            # Check for termination tools before executing
            should_terminate, reason = self._should_terminate(tool_calls)
            if should_terminate:
                self.termination_reason = reason
                self.completed_successfully = reason.startswith("termination_tool_called")
                if self.verbose:
                    print(f"[{self.name}] Terminating: {reason}")

                # Still execute the termination tool call
                if tool_calls:
                    tool_results = await execute_tools(tool_calls, tool_dict)
                    await self.history.add_message("user", tool_results)
                break

            if tool_calls:
                self.iteration_count += 1
                tool_results = await execute_tools(tool_calls, tool_dict)
                await self.history.add_message("user", tool_results)
            else:
                # No tool calls means natural completion
                self.completed_successfully = True
                self.termination_reason = "natural_completion"
                break

        return {
            "final_message": message,
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
                    print(f"[{self.name}] Execution complete:")
                    print(f"  - Reason: {result['termination_reason']}")
                    print(f"  - Success: {result['completed_successfully']}")
                    print(f"  - Iterations: {result['iteration_count']}")
                    print(f"  - Tokens: {result['total_tokens_used']}")

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
    print(response)