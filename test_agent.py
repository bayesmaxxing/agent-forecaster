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
from agents.agent import Agent, ModelConfig


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


async def main():
    """Main test function."""
    if not setup_environment():
        return
    
    # Configure the agent
    config = ModelConfig(
        model="claude-3-7-sonnet-20250219",
        max_tokens=4096,
        temperature=0.7
    )
    
    # System prompt for forecasting agent
    system_prompt = """You are a forecasting agent that helps users make predictions about future events.
    You have access to forecasting tools that allow you to:
    - Get lists of forecasts from different categories
    - Retrieve detailed forecast data and historical points
    - Update forecasts with new predictions and reasoning
    - Query Perplexity for up-to-date information
    
    When helping users with forecasting:
    1. First understand what they want to forecast
    2. Search for relevant existing forecasts if applicable
    3. Gather current information using the query_perplexity tool
    4. Provide well-reasoned predictions with clear explanations
    5. Update forecasts if requested
    
    Be thorough in your analysis and always explain your reasoning."""
    
    # MCP server configuration for forecasting
    mcp_servers = [
        {
            "command": "python",
            "args": ["-m", "agents.tools.forecasting_mcp"],
            "cwd": os.getcwd()
        }
    ]
    
    # Create the agent
    agent = Agent(
        name="ForecastingAgent",
        system=system_prompt,
        config=config,
        mcp_servers=mcp_servers,
        verbose=True
    )
    
    print("=== Forecasting Agent Test ===")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
            
            print("\nAgent is thinking...")
            response = await agent.run_async(user_input)
            
            # Extract and display the final response
            if response and response.content:
                for block in response.content:
                    if block.type == "text":
                        print(f"\nAgent: {block.text}")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again.")


if __name__ == "__main__":
    asyncio.run(main())