#!/usr/bin/env python3
"""Test script for the agent with forecasting MCP.

Usage:
    uv run python test_agent.py

Requirements:
    - Set ANTHROPIC_API_KEY environment variable
    - Optional: Set API_URL, BOT_USERNAME, BOT_PASSWORD for forecasting API
"""

import asyncio
import os
from datetime import datetime
from typing import List
from agents.agent import Agent, ModelConfig
from agents.tools import SubagentManagerTool, ThinkTool
from agents.tools import Tool

def setup_environment():
    """Set up environment variables for testing."""
    # Check if ANTHROPIC_API_KEY is set
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable is required")
        print("Please set it with: export ANTHROPIC_API_KEY=your_api_key")
        return False
    
    # Set default values for forecasting MCP if not already set
    if not os.environ.get("API_URL"):
        os.environ["API_URL"] = "http://localhost:8000"  # Default forecasting API
    
    if not os.environ.get("BOT_USERNAME"):
        os.environ["BOT_USERNAME"] = "test_bot"
    
    if not os.environ.get("BOT_PASSWORD"):
        os.environ["BOT_PASSWORD"] = "test_password"
    
    return True

class CoordinatorAgent:
    def __init__(self, tools: List[Tool]):
        self.coordinator = Agent(
            name="CoordinatorAgent",
            system="""You are a coordinator agent that manages a team of specialized subagents.
            Your role is to:
            1. Analyze problems and break them down into subtasks
            2. Create specialized subagents for each subtask
            3. Coordinate the subagents' work
            4. Synthesize their results into a final solution
            
            You have access to the create_subagent tool to spawn new agents as needed.
            Choose the appropriate model and tools for each subagent based on their task.
            """,
            tools=tools,
            config=ModelConfig(
                model="claude-opus-4-20250514",
                max_tokens=4096,
                temperature=1.0
            )
        )
    
    #TODO: figure out the prompt here...
    async def run_forecasting_workflow(self):
        response = await self.coordinator.run_async(f"""
        You are a superforecaster that is tasked with forecasting the future. 
        
        Please:
        1. Create appropriate subagents for this task
        2. Coordinate their work
        3. Synthesize their findings into a final forecast
        """)
        return response


async def main():
    """Main test function."""
    if not setup_environment():
        return
    
    # Configure the agent
    tools = [SubagentManagerTool(), ThinkTool(), SharedMemoryTool()]
    coordinator = CoordinatorAgent(tools)

    
    
    print("=== Forecasting Agent Test ===")
    
    while True:
        try:
            response = await coordinator.run_async("Run autonomous superforecasting workflow.")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again.")


if __name__ == "__main__":
    asyncio.run(main())