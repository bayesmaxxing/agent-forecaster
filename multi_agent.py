"""
Multi-agent system for forecasting.
"""

import asyncio
import os
import argparse
from datetime import datetime
from agents.agent import Agent, ModelConfig
from agents.tools import SubagentManagerTool, SharedMemoryManagerTool
from agents.tools.shared_memory_tool import SharedMemoryTool

def setup_environment():
    """Set up environment variables."""
    
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY environment variable is required")
        print("Please set it with: export OPENROUTER_API_KEY=your_api_key")
        return False
    
    return True


async def main(model: str, verbose: bool):
    """Main function for multi-agent system."""
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
    elif model.lower() == "multi":
        model_name = "x-ai/grok-4-fast:free"
    else:
        print("Invalid model. Please choose between Gemini, GPT-5, Grok, Opus, or Multi.")
        return
    
    # Configure the agent
    config = ModelConfig(
        model=model_name,
        max_tokens=8192,
        temperature=1.0,
        context_window_tokens=80000
    )
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    system_prompt = open("multi_agent_prompt.md", "r").read()
    system_prompt = system_prompt.replace("{current_date}", current_date)

    subagent_tool = SubagentManagerTool()
    shared_memory_manager_tool = SharedMemoryManagerTool()
    shared_memory_tool = SharedMemoryTool(agent_name="Orchestrator", task_id="multi_agent_session")

    # Create the Orchestrator agent
    agent = Agent(
        name="Orchestrator",
        system=system_prompt,
        config=config,
        mcp_servers=[],
        tools = [subagent_tool, shared_memory_manager_tool, shared_memory_tool],
        verbose=verbose,
    )
    
    print("=== Multi-Agent System ===")
    
    while True:
        try:
            
            response = await agent.run_async(user_input="Be creative in how you forecast!")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forecasting Agent")
    parser.add_argument("-m", "--model", type=str, default="grok", help="Model to use. Choose between Anthropic Opus, OpenAI GPT-5, or Grok")
    parser.add_argument("-v", "--verbose", type=bool, default=False, help="Verbose mode")

    args = parser.parse_args()

    if args.model.lower() not in ["opus", "gpt-5", "grok", "gemini", "multi"]:
        print("Invalid model. Please choose between Anthropic Opus, OpenAI GPT-5, Grok, or Gemini.")
        exit()
    
    
    print(f"Running with model: {args.model}")
    print(f"Running with verbose: {args.verbose}")
    setup_environment()
    asyncio.run(main("multi", args.verbose))
