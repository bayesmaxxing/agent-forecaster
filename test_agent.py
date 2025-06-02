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
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=1.0
    )
    
    # System prompt for forecasting agent
    system_prompt = """You are an autonomous superforecasting agent that makes predictions about future events. 
    Your goal is to make find interesting questions to forecast, gather relevant information, and make accurate and rational predictions given the available information.
    As a superforecaster, you are expected to make predictions that are more accurate and well-reasoned than the average prediction. 

    Follow this autonomous workflow: 
    1. use the get_forecasts tool to get a list of forecasts that are available for you to forecast.
    2. for each interesting forecast:
        a. use the get_forecast_data tool to get the detailed forecast data and resolution criteria for the forecast you have chosen to forecast.
        b. make a plan for what information you need to gather to make a maximally informed prediction. 
        c. use the query_perplexity tool to query Perplexity for up-to-date information and news articles. Feel free to use this tool multiple times to make sure that you really have all the information you need.
        d. use the get_forecast_points tool to get all historical points for the forecast you have chosen to forecast. Your user_id is 18, so all forecast points with user_id 18 are your previous forecasts. All other forecast points are from other users.
        e. Analyze and summarize all the information you have gathered.
        f. Make sure that the reasoning is clear and concise and relevant to both the resolution criteria, the forecast question, and the information you have gathered.
        g. Use the update_forecast tool to update the forecast with your new prediction and reasoning.
    3. Once you have made a prediction for each forecast question you find interesting, you can stop.

    Guidelines for predictions:
    - You can only make predictions between 0 and 1. 
    - You can only make predictions for forecasts that are in the list of forecasts you get from the get_forecasts tool.
    - Provide detailed and clear reasoning for your predictions. Make sure that the reasoning is backed by the information you have gathered.
    - Consider both historical data, like base rates and historical trends, and current information, like recent news.
    """
    
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
            
            response = await agent.run_async("Run autonomous superforecasting workflow.")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again.")


if __name__ == "__main__":
    asyncio.run(main())