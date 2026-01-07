"""
Multi-agent system for forecasting.
"""

import asyncio
import os
import argparse
import shutil
from datetime import datetime
from agents.agent import Agent, ModelConfig
from agents.tools import SubagentManagerTool
from agents.tools.forecasting_tools import GetPointsCreatedToday
from agents.tools.persistent_memory_tool import PersistentMemoryTool
from agents.tools.local_tools import (
    LocalBashTool,
    LocalReadFileTool,
    LocalWriteFileTool,
    LocalListFilesTool,
    WorkspaceManager,
)
from agents.utils.logging_util import set_session_logger, cleanup_session_logger

def setup_environment():
    """Set up environment variables."""
    
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("❌ Error: OPENROUTER_API_KEY environment variable is required")
        print("Please set it with: export OPENROUTER_API_KEY=your_api_key")
        return False
    
    return True


def clear_workspace():
    """Clear all files from the multi_agent_workspace directory."""
    workspace_path = "multi_agent_workspace"

    if os.path.exists(workspace_path):
        try:
            # Remove all files and subdirectories in workspace
            for filename in os.listdir(workspace_path):
                file_path = os.path.join(workspace_path, filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Remove file or link
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove directory and all contents

            print(f"✅ Cleared all files from {workspace_path}/")
        except Exception as e:
            print(f"❌ Error clearing {workspace_path}/: {e}")
    else:
        print(f"ℹ️  Directory {workspace_path}/ does not exist")


async def main(model: str, verbose: bool):
    """Main function for multi-agent system."""
    if not setup_environment():
        return
    
    if model.lower() == "gemini":
        model_name = "google/gemini-3-pro-preview"
    elif model.lower() == "claude":
        model_name = "anthropic/claude-opus-4.5"
    elif model.lower() == "multi":
        model_name = "openai/gpt-5"
    
    # Configure the agent
    config = ModelConfig(
        model=model_name,
        max_tokens=8192,
        temperature=0.8,
        context_window_tokens=400000
    )
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    
    system_prompt = open("prompts/multi_agent_prompt_v2.md", "r").read()
    system_prompt = system_prompt.replace("{current_date}", current_date)

    # Create subagent manager tool (has its own workspace)
    subagent_tool = SubagentManagerTool()

    # Local filesystem tools for orchestrator (use same workspace as subagents)
    orchestrator_workspace = subagent_tool.workspace
    bash_tool = LocalBashTool(workspace=orchestrator_workspace)
    read_file_tool = LocalReadFileTool(workspace=orchestrator_workspace)
    write_file_tool = LocalWriteFileTool(workspace=orchestrator_workspace)
    list_files_tool = LocalListFilesTool(workspace=orchestrator_workspace)

    persistent_memory_tool = PersistentMemoryTool()
    get_points_created_today_tool = GetPointsCreatedToday(model="multi")

    # Create the Orchestrator agent
    agent = Agent(
        name="Orchestrator",
        system=system_prompt,
        config=config,
        tools=[
            subagent_tool,
            bash_tool,
            read_file_tool,
            write_file_tool,
            list_files_tool,
            persistent_memory_tool,
            get_points_created_today_tool
        ],
        verbose=verbose,
    )
    
    # Initialize session logger
    session_id = f"multi_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session_logger = set_session_logger(session_id)

    session_logger.log_agent_action(
        agent_name="System",
        action="Multi-Agent System Starting"
    )
    
    # Autonomous mode - agent decides when to stop
    cycle_count = 0

    session_logger.log_agent_action(
        agent_name="System",
        action="Starting autonomous forecasting session",
        details="Agent will work until it decides it's accomplished its goals"
    )

    while True:
        try:
            cycle_count += 1
            session_logger.log_cycle(cycle_count)

            # Give the agent autonomy to decide what to do next
            if cycle_count == 1:
                prompt = "Begin autonomous forecasting. Analyze available forecasts, create a strategic plan, and work toward producing high-quality forecasts. Use the filesystem (multi_agent_workspace/) for working memory and coordination. When you feel you have accomplished meaningful forecasting work and there's no more valuable work to do in this session, respond with 'AUTONOMOUS_SESSION_COMPLETE' to end gracefully."
            else:
                prompt = "Continue your autonomous work from where you left off. Check your previous progress in the filesystem (use list_files and read_file) and decide on next steps. If you feel the session should end because you've accomplished your goals, respond with 'AUTONOMOUS_SESSION_COMPLETE'."

            response = await agent.run_async(user_input=prompt)

            # Check if agent wants to complete the session
            # Look for completion signals in the response
            if hasattr(response, 'content') and "AUTONOMOUS_SESSION_COMPLETE" in str(response.content):
                session_logger.log_session_end("Agent completed autonomous session")
                break

        except KeyboardInterrupt:
            session_logger.log_session_end("Interrupted by user")
            break
        except Exception as e:
            session_logger.log_error(
                agent_name="Orchestrator",
                error=str(e),
                context=f"Cycle {cycle_count}"
            )
            session_logger.log_agent_action(
                agent_name="System",
                action="Continuing to next cycle"
            )

    # Cleanup
    cleanup_session_logger()
    clear_workspace()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forecasting Agent")
    parser.add_argument("-v", "--verbose", type=bool, default=False, help="Verbose mode")
    parser.add_argument("-m", "--model", type=str, default="multi", help="Model to use. Choose between Gemini, Claude, or Multi")
    args = parser.parse_args()

    print(f"Running with verbose: {args.verbose}")
    print("Check logs/ directory for detailed session logs with improved formatting.")
    setup_environment()
    asyncio.run(main(args.model, args.verbose))
