"""Agent implementation with OpenAI SDK and tools."""

import asyncio
import os
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any
import logging
from datetime import datetime

from openai import OpenAI

from agents.types import Tool

from agents.utils.history_util import MessageHistory
from agents.utils.tool_util import execute_tools
from agents.utils.connections import setup_mcp_connections

# Set up logging
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)
log_filename = os.path.join(LOGS_DIR, f'agent_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('ForecastingAgent')

@dataclass
class ModelConfig:
    """Configuration settings for OpenRouter model parameters."""

    model: str = "anthropic/claude-3.5-sonnet"
    max_tokens: int = 4096
    temperature: float = 1.0
    context_window_tokens: int = 180000


class Agent:
    """OpenRouter-powered agent with tool use capabilities."""

    def __init__(
        self,
        name: str,
        system: str,
        tools: list[Tool] | None = None,
        mcp_servers: list[dict[str, Any]] | None = None,
        config: ModelConfig | None = None,
        verbose: bool = False,
        client: OpenAI | None = None,
    ):
        self.name = name
        self.system = system
        self.verbose = verbose
        self.tools = list(tools or [])
        self.config = config or ModelConfig()
        self.mcp_servers = mcp_servers or []
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
            print(f"\n[{self.name}] Agent initialized")

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
            print(f"\n[{self.name}] Received: {user_input}")
        await self.history.add_message("user", user_input, None)

        tool_dict = {tool.name: tool for tool in self.tools}

        while True:
            self.history.truncate()
            params = self._prepare_api_params()
            
            response = self.client.chat.completions.create(**params)
            logger.info(f"Response: {response}")
            logger.info(f"Input tokens: {response.usage.prompt_tokens}")
            logger.info(f"Output tokens: {response.usage.completion_tokens}")
            
            message = response.choices[0].message
            tool_calls = message.tool_calls or []
            logger.info(f"Tool calls: {tool_calls}")
            if self.verbose:
                if message.content:
                    print(f"\n[{self.name}] Output: {message.content}")
                    logger.info(f"Output: {message.content}")
                
                for tool_call in tool_calls:
                    print(
                        f"\n[{self.name}] Tool call: "
                        f"{tool_call.function.name}({tool_call.function.arguments})"
                    )
                    logger.info(f"Tool call: {tool_call.function.name}({tool_call.function.arguments})")
            
            await self.history.add_message(
                "assistant", message, response.usage
            )

            if tool_calls:
                tool_results = await execute_tools(
                    tool_calls,
                    tool_dict,
                )
                if self.verbose:
                    for block in tool_results:
                        content = block.get('content', '')
                        print(
                            f"\n[{self.name}] Tool result: "
                            f"{content}"
                        )
                        logger.info(f"Tool result: {content}")
                await self.history.add_message("user", tool_results)
            else:
                return message

    async def run_async(self, user_input: str) -> list[dict[str, Any]]:
        """Run agent with MCP tools asynchronously."""
        async with AsyncExitStack() as stack:
            original_tools = list(self.tools)

            try:
                mcp_tools = await setup_mcp_connections(
                    self.mcp_servers, stack
                )
                self.tools.extend(mcp_tools)
                return await self._agent_loop(user_input)
            finally:
                self.tools = original_tools

    def run(self, user_input: str) -> list[dict[str, Any]]:
        """Run agent synchronously"""
        return asyncio.run(self.run_async(user_input))
