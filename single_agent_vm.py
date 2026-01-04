#!/usr/bin/env python3
"""Local forecasting agent with workspace sandboxing and full capabilities.

This agent has access to:
- Sandboxed workspace directory (persists across sessions)
- Network access for downloading data
- Full local Python environment
- Bash, file read/write/edit tools (Claude Code style)

All operations are restricted to the agent_workspace/ directory.

Usage:
    uv run python single_agent_vm.py
    uv run python single_agent_vm.py -m opus|gpt-5|grok|gemini -v true

Requirements:
    - Set OPENROUTER_API_KEY environment variable
"""

import asyncio
import os
import argparse
from datetime import datetime
from agents.agent import Agent, ModelConfig
from agents.tools import (
    QueryPerplexityTool,
    LocalBashTool,
    LocalReadFileTool,
    LocalWriteFileTool,
    LocalEditFileTool,
    LocalListFilesTool,
    WorkspaceManager,
    set_workspace,
)
from agents.tools.forecasting_tools import (
    GetForecastsTool,
    GetForecastDataTool,
    GetForecastPointsTool,
    UpdateForecastTool,
)
from agents.utils.logging_util import set_session_logger, cleanup_session_logger


def setup_environment():
    """Set up environment variables for testing."""
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY environment variable is required")
        print("Please set it with: export OPENROUTER_API_KEY=your_api_key")
        return False

    if not os.environ.get("API_URL"):
        os.environ["API_URL"] = "http://localhost:8000"

    return True

async def main(model: str, verbose: bool):
    """Main function."""
    if not setup_environment():
        return

    model_map = {
        "gemini": "google/gemini-3-pro-preview",
        "gpt-5": "openai/gpt-5",
        "grok": "x-ai/grok-4.1-fast",
        "opus": "anthropic/claude-opus-4.5",
    }

    model_name = model_map.get(model.lower())
    if not model_name:
        print(f"Invalid model. Choose from: {', '.join(model_map.keys())}")
        return

    # Initialize workspace
    workspace = WorkspaceManager()
    set_workspace(workspace)
    print(f"Workspace initialized: {workspace.workspace}")

    # Configure the agent
    config = ModelConfig(
        model=model_name,
        max_tokens=4096,
        temperature=1.0,
    )

    current_date = datetime.now().strftime("%Y-%m-%d")
    system_prompt = open("prompts/prompt_v2.md", "r").read()
    system_prompt = system_prompt.replace("{current_date}", current_date)

    # Initialize tools
    tools = [
        LocalBashTool(),
        LocalReadFileTool(),
        LocalWriteFileTool(),
        LocalEditFileTool(),
        LocalListFilesTool(),
        # Forecasting API tools
        GetForecastsTool(model=model),
        GetForecastDataTool(),
        GetForecastPointsTool(model=model),
        UpdateForecastTool(model=model),
        # Information tools
        QueryPerplexityTool(),
    ]

    # Create the agent
    agent = Agent(
        name="ForecastingAgent",
        system=system_prompt,
        config=config,
        tools=tools,
        verbose=verbose,
    )

    # Initialize session logger
    session_id = f"single_agent_local_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session_logger = set_session_logger(session_id)

    session_logger.log_agent_action(
        agent_name="System",
        action="Local Agent Starting",
    )

    cycle_count = 0

    try:
        while True:
            try:
                cycle_count += 1
                session_logger.log_cycle(cycle_count)

                if cycle_count == 1:
                    prompt = """Begin autonomous forecasting. You have access to a sandboxed workspace where you can:
- Download data from the internet
- Create and run Python scripts
- Build up tools and utilities over time
- Store data and analysis results

First, use list_files to explore your workspace. Then analyze available forecasts and work toward producing high-quality forecasts.
When you feel you have accomplished meaningful work, respond with 'AUTONOMOUS_SESSION_COMPLETE' to end gracefully."""
                else:
                    prompt = """Continue your autonomous work. Check your workspace for any previous work and decide on next steps.
If you feel the session should end, respond with 'AUTONOMOUS_SESSION_COMPLETE'."""

                response = await agent.run_async(user_input=prompt)

                if hasattr(response, "content") and "AUTONOMOUS_SESSION_COMPLETE" in str(
                    response.content
                ):
                    session_logger.log_session_end("Agent completed autonomous session")
                    break

            except KeyboardInterrupt:
                session_logger.log_session_end("Interrupted by user")
                break
            except Exception as e:
                session_logger.log_error(
                    agent_name="ForecastingAgent",
                    error=str(e),
                    context="Main loop",
                )
                session_logger.log_agent_action(
                    agent_name="System",
                    action="Error occurred, continuing",
                )

    finally:
        cleanup_session_logger()
        print("Session ended.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local Forecasting Agent with Workspace")
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default="opus",
        help="Model to use: opus, gpt-5, grok, or gemini",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        type=bool,
        default=False,
        help="Verbose mode",
    )

    args = parser.parse_args()

    if args.model.lower() not in ["opus", "gpt-5", "grok", "gemini"]:
        print("Invalid model. Choose from: opus, gpt-5, grok, gemini")
        exit(1)

    print(f"Running local agent with model: {args.model}")
    print(f"Verbose: {args.verbose}")
    print("Check logs/ directory for detailed session logs.")
    print("-" * 50)

    asyncio.run(main(args.model, args.verbose))
