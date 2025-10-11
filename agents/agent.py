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
class ModelConfig:
    """Configuration settings for OpenRouter model parameters."""

    model: str = "openai/gpt-5"
    max_tokens: int = 8192
    temperature: float = 1.0
    context_window_tokens: int = 80000


class Agent:
    """OpenRouter-powered agent with tool use capabilities."""

    def __init__(
        self,
        name: str,
        system: str,
        tools: list[Tool] | None = None,
        config: ModelConfig | None = None,
        verbose: bool = False,
        client: OpenAI | None = None,
    ):
        self.name = name
        self.system = system
        self.verbose = verbose
        self.tools = list(tools or [])
        self.config = config or ModelConfig()
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
            session_logger.log_agent_action(
                agent_name=self.name,
                action="Initialized",
                agent_type=AgentType.ORCHESTRATOR,
                level=LogLevel.INFO
            )

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

    async def _agent_loop(self, user_input: str) -> list[dict[str, Any]]:
        """Process user input and handle tool calls in a loop"""
        if self.verbose:
            session_logger = get_session_logger()
            session_logger.log_agent_action(
                agent_name=self.name,
                action=f"Received task",
                details=user_input[:100] + "..." if len(user_input) > 100 else user_input
            )
        await self.history.add_message("user", user_input, None)

        tool_dict = {tool.name: tool for tool in self.tools}

        while True:
            self.history.truncate()
            params = self._prepare_api_params()
            
            response = self.client.chat.completions.create(**params)

            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            if self.verbose:
                session_logger = get_session_logger()

                # Extract reasoning if available (for models that support it)
                reasoning = None
                if hasattr(message, 'reasoning') and message.reasoning:
                    reasoning = message.reasoning

                # Log the full LLM response
                session_logger.log_llm_response(
                    agent_name=self.name,
                    content=message.content,
                    reasoning=reasoning,
                    model=response.model if hasattr(response, 'model') else self.config.model,
                    tokens=response.usage.total_tokens if response.usage else None,
                    indent=0
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
                        params=params_dict
                    )
            
            await self.history.add_message(
                "assistant", message, response.usage
            )

            if tool_calls:
                tool_results = await execute_tools(
                    tool_calls,
                    tool_dict,
                )
                if self.verbose:
                    for i, block in enumerate(tool_results):
                        content = block.get('content', '')
                        summary = content
                        tool_name = tool_calls[i].function.name if i < len(tool_calls) else "unknown"

                        session_logger.log_tool_call(
                            agent_name=self.name,
                            tool_name=tool_name,
                            result_summary=summary
                        )
                        
                await self.history.add_message("user", tool_results)
            else:
                return message

    async def run_async(self, user_input: str) -> list[dict[str, Any]]:
        """Run agent asynchronously."""
        async with AsyncExitStack() as stack:
            original_tools = list(self.tools)

            try:
                return await self._agent_loop(user_input)
            finally:
                self.tools = original_tools

    def run(self, user_input: str) -> list[dict[str, Any]]:
        """Run agent synchronously"""
        return asyncio.run(self.run_async(user_input))

if __name__ == "__main__":
    agent = Agent(
        name="TestAgent",
        system="You are a test agent.",
        tools=[],
        config=ModelConfig(),
        verbose=True
    )

    response = agent.run("What is the weather in Tokyo?")
    print(response)