from typing import List, Optional, TYPE_CHECKING, Dict, Any
from dataclasses import dataclass
import asyncio
import time
from agents.types import Tool
from .information_tools import QueryPerplexityTool
from .forecasting_tools import GetForecastsTool, GetForecastDataTool, GetForecastPointsTool, UpdateForecastTool, GetPointsCreatedToday
from .code_executor_tool import CodeExecutorTool
from agents.tools.reporting_tool import ReportResultsTool, RequestGuidanceTool
from agents.tools.shared_memory_tool import SharedMemoryTool

if TYPE_CHECKING:
    from agents.subagent import Subagent, SubagentConfig


class SubagentManagerTool(Tool):
    def __init__(self):
        super().__init__(
            name="subagent_manager",
            description="Manage subagents with specific capabilities, goals, and execution limits",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "run", "delete", "status", "list", "run_parallel", "run_batch"],
                        "description": "The action to perform on subagents."
                    },
                    "name": {
                        "type": "string",
                        "description": "Unique name for the subagent (required for create, run, delete, and status actions)"
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "System prompt defining the subagent's role and goals (required for create action)"
                    },
                    "task_input": {
                        "type": "string",
                        "description": "Specific task or input to give the subagent (required for run action)"
                    },
                    "tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tool names this subagent should have access to. Available: query_perplexity, code_executor, get_forecasts, get_forecast_data, get_forecast_points, update_forecast, get_points_created_today, shared_memory. Note: report_results and request_guidance are automatically included (required for create action)"
                    },
                    "model": {
                        "type": "string",
                        "description": "Model to use for this subagent (required for create action)",
                        "enum": ["x-ai/grok-4-fast", "google/gemini-3-pro-preview", "anthropic/claude-haiku-4.5"]
                    },
                    "max_iterations": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 50,
                        "description": "Maximum number of tool call iterations (optional for create action)"
                    },
                    "termination_tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tools that end execution when called (optional for create action)"
                    },
                    "require_termination_tool": {
                        "type": "boolean",
                        "default": False,
                        "description": "Whether a termination tool must be called for successful completion (optional for create action)"
                    },
                    "subagent_tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Name of the subagent to run"},
                                "task_input": {"type": "string", "description": "Task input for the subagent"}
                            },
                            "required": ["name", "task_input"]
                        },
                        "description": "List of subagent tasks for parallel/batch execution (required for run_parallel and run_batch actions)"
                    },
                },
                "required": ["action"],
            }
        )

        self.subagents = {}

    async def execute(self, action: str, **kwargs) -> str:
        if action == "create":
            return await self._create_subagent(**kwargs)
        elif action == "run":
            return await self._run_subagent(**kwargs)
        elif action == "run_parallel":
            return await self._run_subagents_parallel(**kwargs)
        elif action == "run_batch":
            return await self._run_subagents_batch(**kwargs)
        elif action == "delete":
            return self._delete_subagent(**kwargs)
        elif action == "status":
            return self._get_subagent_status(**kwargs)
        elif action == "list":
            return self._list_subagents()
        else:
            return f"Error: Invalid action '{action}'"
        
    async def _create_subagent(
        self,
        name: str,
        system_prompt: str,
        tools: List[str],
        model: str,
        max_iterations: int = 10,
        termination_tools: List[str] = None,
        require_termination_tool: bool = False,
        **kwargs
    ) -> str:
        # Import here to avoid circular imports
        from agents.subagent import Subagent, SubagentConfig

        if name in self.subagents:
            return f"Error: Subagent '{name}' already exists"

        # Get the requested tools
        agent_tools = []

        # Always add coordination tools
        agent_tools.append(ReportResultsTool())
        agent_tools.append(RequestGuidanceTool())
        agent_tools.append(SharedMemoryTool(agent_name=name, task_id="multi_agent_session"))

        for tool_name in tools:
            if tool_name == "query_perplexity":
                agent_tools.append(QueryPerplexityTool())
            elif tool_name == "get_forecasts":
                agent_tools.append(GetForecastsTool(model="multi"))
            elif tool_name == "get_forecast_data":
                agent_tools.append(GetForecastDataTool())
            elif tool_name == "get_forecast_points":
                agent_tools.append(GetForecastPointsTool(model="multi"))
            elif tool_name == "update_forecast":
                agent_tools.append(UpdateForecastTool(model="multi"))
            elif tool_name == "get_points_created_today":
                agent_tools.append(GetPointsCreatedToday(model="multi"))
            elif tool_name == "code_executor":
                agent_tools.append(CodeExecutorTool())
            elif tool_name == "shared_memory":
                # Already added above, but allow explicit inclusion
                continue
            elif tool_name in ["report_results", "request_guidance"]:
                # Already added above
                continue
            else:
                return f"Error: Tool '{tool_name}' not available. Available tools: query_perplexity, code_executor, get_forecasts, get_forecast_data, get_forecast_points, update_forecast, get_points_created_today, shared_memory, report_results, request_guidance"

        # Set up termination tools (default to report_results if none specified)
        if termination_tools is None:
            termination_tools = ["report_results"]

        config = SubagentConfig(
            model=model,
            max_tokens=30000,
            temperature=1.0,
            max_iterations=max_iterations,
            max_total_tokens=200000,
            termination_tools=termination_tools,
            require_termination_tool=require_termination_tool
        )

        self.subagents[name] = Subagent(
            name=name,
            system=system_prompt,
            tools=agent_tools,
            config=config,
            verbose=True
        )

        return f"Successfully created subagent '{name}' with {len(agent_tools)} tools (max_iterations: {max_iterations}, termination_tools: {termination_tools})"
        
    async def _run_subagent(self, name: str, task_input: str, **kwargs) -> str:
        if name not in self.subagents:
            return f"Error: Subagent '{name}' does not exist"

        try:
            result = await self.subagents[name].run_async(task_input)

            # Format detailed execution report
            status_emoji = "✅" if result["completed_successfully"] else "❌"
            final_content = result["final_message"].get("content", "") if result["final_message"] else ""
            report = f"""
SUBAGENT EXECUTION REPORT: {name} {status_emoji}
================================================
Task Input: {task_input[:100]}{'...' if len(task_input) > 100 else ''}

EXECUTION SUMMARY:
- Status: {"SUCCESS" if result["completed_successfully"] else "INCOMPLETE/FAILED"}
- Termination Reason: {result["termination_reason"]}
- Iterations Used: {result["iteration_count"]}
- Tokens Used: {result["total_tokens_used"]}

FINAL OUTPUT:
{final_content if final_content else "No final message content"}

{'=' * 50}
"""
            return report

        except Exception as e:
            return f"Error: Failed to run subagent '{name}': {e}"

    def _delete_subagent(self, name: str, **kwargs) -> str:
        if name not in self.subagents:
            return f"Error: Subagent '{name}' does not exist"
        del self.subagents[name]
        return f"Successfully deleted subagent '{name}'"

    def _get_subagent_status(self, name: str, **kwargs) -> str:
        if name not in self.subagents:
            return f"Error: Subagent '{name}' does not exist"

        subagent = self.subagents[name]
        status = subagent.get_execution_status()

        return f"""
SUBAGENT STATUS: {name}
=====================
Current Iterations: {status["iteration_count"]}/{status["max_iterations"]}
Current Token Usage: {status["total_tokens_used"]}/{status["max_total_tokens"]}
Termination Reason: {status["termination_reason"] or "Not yet executed"}
Completed Successfully: {status["completed_successfully"]}
Termination Tools: {status["termination_tools"]}
Requires Termination Tool: {status["require_termination_tool"]}

System Prompt: {subagent.system[:200]}{'...' if len(subagent.system) > 200 else ''}
Available Tools: {[tool.name for tool in subagent.tools]}
"""

    def _list_subagents(self) -> str:
        if not self.subagents:
            return "No subagents exist"

        subagent_list = []
        for name, subagent in self.subagents.items():
            status = subagent.get_execution_status()
            status_indicator = "✅" if status["completed_successfully"] else ("🔄" if status["iteration_count"] > 0 else "⏸️")
            subagent_list.append(
                f"{status_indicator} {name}: {subagent.system[:80]}{'...' if len(subagent.system) > 80 else ''}"
            )

        return "Existing subagents:\n" + "\n".join(subagent_list)

    async def _run_subagents_parallel(
        self,
        subagent_tasks: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """Run multiple subagents in parallel."""
        if not subagent_tasks:
            return "Error: No subagent tasks provided"

        # Validate all subagents exist
        missing_agents = []
        for task in subagent_tasks:
            if task["name"] not in self.subagents:
                missing_agents.append(task["name"])
        
        if missing_agents:
            return f"Error: Subagents not found: {', '.join(missing_agents)}"

        try:
            # Execute subagents in parallel
            results = await asyncio.gather(
                *[self._run_subagent(task["name"], task["task_input"]) for task in subagent_tasks],
                return_exceptions=True
            )

            # Process results
            successful_results = []
            failed_results = []
            
            for i, result in enumerate(results):
                task = subagent_tasks[i]
                if isinstance(result, Exception):
                    failed_results.append(f"❌ {task['name']}: {str(result)}")
                else:
                    successful_results.append(result)

            # Format comprehensive report
            report = f"""
PARALLEL SUBAGENT EXECUTION REPORT
==================================
Executed {len(subagent_tasks)} subagents in parallel

SUCCESSFUL EXECUTIONS ({len(successful_results)}):
{chr(10).join(successful_results)}

FAILED EXECUTIONS ({len(failed_results)}):
{chr(10).join(failed_results)}
"""
            return report

        except Exception as e:
            return f"Error: Parallel execution failed: {str(e)}"

    async def _run_subagents_batch(
        self,
        subagent_tasks: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """Run multiple subagents sequentially (batch mode)."""
        if not subagent_tasks:
            return "Error: No subagent tasks provided"

        # Validate all subagents exist
        missing_agents = []
        for task in subagent_tasks:
            if task["name"] not in self.subagents:
                missing_agents.append(task["name"])
        
        if missing_agents:
            return f"Error: Subagents not found: {', '.join(missing_agents)}"

        results = []
        for task in subagent_tasks:
            try:
                result = await self._run_subagent(task["name"], task["task_input"])
                results.append(result)
            except Exception as e:
                results.append(f"❌ {task['name']}: Error - {str(e)}")

        return f"""
BATCH SUBAGENT EXECUTION REPORT
===============================
Executed {len(subagent_tasks)} subagents sequentially

RESULTS:
{chr(10).join(results)}
"""
