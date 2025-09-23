#!/usr/bin/env python3
"""Test script for the agent with forecasting MCP.

Usage:
    uv run python test_agent.py

Requirements:
    - Set OPENROUTER_API_KEY environment variable
    - Optional: Set API_URL, BOT_USERNAME, BOT_PASSWORD for forecasting API
"""

import asyncio
import os
import argparse
from datetime import datetime
from agents.agent import Agent, ModelConfig
from agents.tools import ThinkTool, QueryPerplexityTool, RequestFeedbackTool
from agents.tools.forecasting_tools import GetForecastsTool, GetForecastDataTool, GetForecastPointsTool, UpdateForecastTool

def setup_environment():
    """Set up environment variables for testing."""
    # Check if OPENROUTER_API_KEY is set
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY environment variable is required")
        print("Please set it with: export OPENROUTER_API_KEY=your_api_key")
        return False
    
    # Set default values for forecasting MCP if not already set
    if not os.environ.get("API_URL"):
        os.environ["API_URL"] = "http://localhost:8000"  # Default forecasting API
    
    return True


async def main(model: str, verbose: bool):
    """Main test function."""
    if not setup_environment():
        return
    
    if model.lower() == "gemini":
        model_name = "google/gemini-2.5-pro"
    elif model.lower() == "gpt-5":
        model_name = "openai/gpt-5"
    elif model.lower() == "grok":
        model_name = "x-ai/grok-4"
    elif model.lower() == "opus":
        model_name = "anthropic/claude-opus-4.1"
    else:
        print("Invalid model. Please choose between Gemini, GPT-5, Grok, or Opus.")
        return
    
    # Configure the agent
    config = ModelConfig(
        model=model_name,
        max_tokens=4096,
        temperature=1.0
    )
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    system_prompt = open("prompt.md", "r").read()
    system_prompt = system_prompt.replace("{current_date}", current_date)

    think_tool = ThinkTool()
    get_forecasts_tool = GetForecastsTool(model=model)
    get_forecast_data_tool = GetForecastDataTool()
    get_forecast_points_tool = GetForecastPointsTool(model=model)
    update_forecast_tool = UpdateForecastTool(model=model)
    query_perplexity_tool = QueryPerplexityTool()
    request_feedback_tool = RequestFeedbackTool()

    # Create the agent
    agent = Agent(
        name="ForecastingAgent",
        system=system_prompt,
        config=config,
        mcp_servers=[],
        tools = [think_tool, get_forecasts_tool, get_forecast_data_tool, get_forecast_points_tool, update_forecast_tool, query_perplexity_tool, request_feedback_tool],
        verbose=verbose
    )
    
    print("=== Forecasting Agent Test ===")
    
    while True:
        try:
            
            response = await agent.run_async(user_input="Go ahead and forecast!")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forecasting Agent")
    parser.add_argument("-m", "--model", type=str, default="opus", help="Model to use. Choose between Anthropic Opus, OpenAI GPT-5, or Grok")
    parser.add_argument("-v", "--verbose", type=bool, default=False, help="Verbose mode")

    args = parser.parse_args()

    if args.model.lower() not in ["opus", "gpt-5", "grok", "gemini"]:
        print("Invalid model. Please choose between Anthropic Opus, OpenAI GPT-5, Grok, or Gemini.")
        exit()
    
    
    print(f"Running with model: {args.model}")
    print(f"Running with verbose: {args.verbose}")
    setup_environment()
    asyncio.run(main(args.model, args.verbose))
