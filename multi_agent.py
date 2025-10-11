"""
Multi-agent system for forecasting.
"""

import asyncio
import os
import argparse
import shutil
from datetime import datetime
from agents.agent import Agent, ModelConfig
from agents.tools import SubagentManagerTool, SharedMemoryManagerTool, CodeExecutorTool
from agents.tools.shared_memory_tool import SharedMemoryTool, PersistentMemoryTool
from agents.utils.logging_util import set_session_logger, cleanup_session_logger

def setup_environment():
    """Set up environment variables."""
    
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("❌ Error: OPENROUTER_API_KEY environment variable is required")
        print("Please set it with: export OPENROUTER_API_KEY=your_api_key")
        return False
    
    return True


def clear_shared_memory():
    """Clear all files from the /shared_memory directory."""
    shared_memory_path = "shared_memory"
    
    if os.path.exists(shared_memory_path):
        try:
            # Remove all files and subdirectories in shared_memory
            for filename in os.listdir(shared_memory_path):
                file_path = os.path.join(shared_memory_path, filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Remove file or link
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove directory and all contents
            
            print(f"✅ Cleared all files from {shared_memory_path}/")
        except Exception as e:
            print(f"❌ Error clearing {shared_memory_path}/: {e}")
    else:
        print(f"ℹ️  Directory {shared_memory_path}/ does not exist")


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
        model_name = "anthropic/claude-sonnet-4.5"
    else:
        print("❌ Invalid model. Please choose between Gemini, GPT-5, Grok, Opus, or Multi.")
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

    persistent_memory_tool = PersistentMemoryTool()
    code_executor_tool = CodeExecutorTool()

    # Create the Orchestrator agent
    agent = Agent(
        name="Orchestrator",
        system=system_prompt,
        config=config,
        mcp_servers=[],
        tools = [subagent_tool, shared_memory_manager_tool, shared_memory_tool, persistent_memory_tool],
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
                prompt = "Begin autonomous forecasting. Analyze available forecasts, create a strategic plan, and work toward producing high-quality forecasts. When you feel you have accomplished meaningful forecasting work and there's no more valuable work to do in this session, respond with 'AUTONOMOUS_SESSION_COMPLETE' to end gracefully."
            else:
                prompt = "Continue your autonomous work from where you left off. Check your previous progress in shared memory and decide on next steps. If you feel the session should end because you've accomplished your goals, respond with 'AUTONOMOUS_SESSION_COMPLETE'."

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
    clear_shared_memory()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forecasting Agent")
    parser.add_argument("-m", "--model", type=str, default="grok", help="Model to use. Choose between Anthropic Opus, OpenAI GPT-5, or Grok")
    parser.add_argument("-v", "--verbose", type=bool, default=False, help="Verbose mode")

    args = parser.parse_args()

    if args.model.lower() not in ["opus", "gpt-5", "grok", "gemini", "multi"]:
        print("❌ Invalid model. Please choose between Anthropic Opus, OpenAI GPT-5, Grok, or Gemini.")
        exit()
    
    
    print(f"Running with model: {args.model}")
    print(f"Running with verbose: {args.verbose}")
    print("Check logs/ directory for detailed session logs with improved formatting.")
    setup_environment()
    asyncio.run(main("multi", args.verbose))
