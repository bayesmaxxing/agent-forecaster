from typing import List, Optional, TYPE_CHECKING, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path
import asyncio
import json
from agents.types import Tool
from .information_tools import QueryPerplexityTool
from .forecasting_tools import GetForecastsTool, GetForecastDataTool, GetForecastPointsTool, UpdateForecastTool, GetPointsCreatedToday
from .code_executor_tool import CodeExecutorTool
from agents.tools.reporting_tool import ReportResultsTool, RequestGuidanceTool
from agents.tools.local_tools import (
    WorkspaceManager,
    LocalBashTool,
    LocalReadFileTool,
    LocalWriteFileTool,
    LocalListFilesTool,
)

if TYPE_CHECKING:
    from agents.subagent import Subagent, SubagentConfig


class TaskStatus(Enum):
    """Status of an async task execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskExecution:
    """Tracks a single async subagent task execution."""
    task_id: str
    subagent_name: str
    task_input: str
    status: TaskStatus = TaskStatus.PENDING
    asyncio_task: Optional[asyncio.Task] = field(default=None, repr=False)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    iteration_count: int = 0
    tokens_used: int = 0

    def to_status_dict(self) -> dict:
        """Convert to status dictionary for tool response."""
        duration = None
        if self.started_at:
            end_time = self.completed_at or datetime.now()
            duration = (end_time - self.started_at).total_seconds()

        return {
            "task_id": self.task_id,
            "subagent_name": self.subagent_name,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": duration,
            "iteration_count": self.iteration_count,
            "tokens_used": self.tokens_used,
            "has_result": self.result is not None,
            "has_error": self.error is not None,
        }


class SubagentManagerTool(Tool):
    def __init__(self):
        super().__init__(
            name="subagent_manager",
            description="Manage subagents with async fire-and-forget execution. Start tasks in background and monitor their progress.",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "start", "start_parallel", "check_status", "get_result", "cancel", "list_tasks", "delete", "status", "list"],
                        "description": "The action to perform. 'start' runs a subagent in background, 'check_status' monitors progress, 'get_result' retrieves completed results."
                    },
                    "name": {
                        "type": "string",
                        "description": "Unique name for the subagent (required for create, start, delete, status actions)"
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "System prompt defining the subagent's role and goals (required for create action)"
                    },
                    "task_input": {
                        "type": "string",
                        "description": "Specific task or input to give the subagent (required for start action)"
                    },
                    "tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tool names this subagent should have access to. Available: query_perplexity, code_executor, get_forecasts, get_forecast_data, get_forecast_points, update_forecast, get_points_created_today, bash, read_file, write_file, list_files. Note: report_results and request_guidance are automatically included. Use filesystem tools (bash, read_file, write_file) for working memory. (required for create action)"
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
                        "description": "List of subagent tasks for start_parallel action"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Task execution ID (returned by start action, required for check_status/get_result/cancel)"
                    },
                    "task_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Multiple task IDs for batch status checks"
                    },
                    "wait": {
                        "type": "boolean",
                        "default": False,
                        "description": "Whether get_result should block until task completion"
                    },
                    "timeout": {
                        "type": "number",
                        "default": 300,
                        "description": "Timeout in seconds when wait=True"
                    },
                },
                "required": ["action"],
            }
        )

        self.subagents: Dict[str, Any] = {}
        self.running_tasks: Dict[str, TaskExecution] = {}
        self._task_counter: int = 0

        # Create dedicated multi-agent workspace
        self.workspace = WorkspaceManager(
            workspace_path=Path(__file__).parent.parent.parent / "multi_agent_workspace"
        )

    async def execute(self, action: str, **kwargs) -> str:
        if action == "create":
            return await self._create_subagent(**kwargs)
        elif action == "start":
            return await self._start_subagent(**kwargs)
        elif action == "start_parallel":
            return await self._start_subagents_parallel(**kwargs)
        elif action == "check_status":
            return await self._check_status_tasks(**kwargs)
        elif action == "get_result":
            return await self._get_result(**kwargs)
        elif action == "cancel":
            return await self._cancel_task(**kwargs)
        elif action == "list_tasks":
            return await self._list_tasks(**kwargs)
        elif action == "delete":
            return self._delete_subagent(**kwargs)
        elif action == "status":
            return self._get_subagent_status(**kwargs)
        elif action == "list":
            return self._list_subagents()
        else:
            return f"Error: Invalid action '{action}'. Valid actions: create, start, start_parallel, check_status, get_result, cancel, list_tasks, delete, status, list"
        
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
            elif tool_name in ["report_results", "request_guidance"]:
                # Already added above
                continue
            # Local filesystem tools (use multi-agent workspace)
            elif tool_name == "bash":
                agent_tools.append(LocalBashTool(workspace=self.workspace))
            elif tool_name == "read_file":
                agent_tools.append(LocalReadFileTool(workspace=self.workspace))
            elif tool_name == "write_file":
                agent_tools.append(LocalWriteFileTool(workspace=self.workspace))
            elif tool_name == "list_files":
                agent_tools.append(LocalListFilesTool(workspace=self.workspace))
            else:
                return f"Error: Tool '{tool_name}' not available. Available tools: query_perplexity, code_executor, get_forecasts, get_forecast_data, get_forecast_points, update_forecast, get_points_created_today, bash, read_file, write_file, list_files, report_results, request_guidance"

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

    # ==================== ASYNC FIRE-AND-FORGET METHODS ====================

    async def _start_subagent(
        self,
        name: str,
        task_input: str,
        **kwargs
    ) -> str:
        """Start a subagent task in the background without blocking."""
        if name not in self.subagents:
            return f"Error: Subagent '{name}' does not exist. Create it first with action='create'."

        # Generate unique task ID
        self._task_counter += 1
        task_id = f"task_{name}_{self._task_counter}_{datetime.now().strftime('%H%M%S')}"

        # Create task execution record
        task_exec = TaskExecution(
            task_id=task_id,
            subagent_name=name,
            task_input=task_input,
            status=TaskStatus.PENDING,
            started_at=datetime.now()
        )

        # Create the async wrapper that tracks execution
        async def run_with_tracking():
            task_exec.status = TaskStatus.RUNNING
            try:
                result = await self.subagents[name].run_async(task_input)
                task_exec.result = result
                task_exec.status = TaskStatus.COMPLETED
                task_exec.iteration_count = result.get("iteration_count", 0)
                task_exec.tokens_used = result.get("total_tokens_used", 0)

                # Store result to filesystem
                await self._store_result_to_filesystem(task_id, task_exec)

            except asyncio.CancelledError:
                task_exec.status = TaskStatus.CANCELLED
                task_exec.error = "Task was cancelled"
                raise
            except Exception as e:
                task_exec.status = TaskStatus.FAILED
                task_exec.error = str(e)
                # Log error
                try:
                    from agents.utils.logging_util import get_session_logger
                    logger = get_session_logger()
                    logger.log_error(agent_name=name, error=str(e), context=f"Background task {task_id}")
                except Exception:
                    pass
            finally:
                task_exec.completed_at = datetime.now()

        # Schedule the task
        task_exec.asyncio_task = asyncio.create_task(run_with_tracking())
        self.running_tasks[task_id] = task_exec

        return f"""
SUBAGENT TASK STARTED
=====================
Task ID: {task_id}
Subagent: {name}
Task Input: {task_input[:200]}{'...' if len(task_input) > 200 else ''}
Started At: {task_exec.started_at.isoformat()}

Use action="check_status" with task_id="{task_id}" to monitor progress.
Use action="get_result" with task_id="{task_id}" to retrieve results when complete.
"""

    async def _start_subagents_parallel(
        self,
        subagent_tasks: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """Start multiple subagent tasks in the background without blocking."""
        if not subagent_tasks:
            return "Error: No subagent tasks provided"

        # Validate all subagents exist
        missing_agents = [t["name"] for t in subagent_tasks if t["name"] not in self.subagents]
        if missing_agents:
            return f"Error: Subagents not found: {', '.join(missing_agents)}"

        task_ids = []
        for task in subagent_tasks:
            # Start each task (this returns immediately)
            result = await self._start_subagent(
                name=task["name"],
                task_input=task["task_input"]
            )
            # Extract task_id from result
            for line in result.split('\n'):
                if line.startswith('Task ID:'):
                    task_ids.append(line.split(':', 1)[1].strip())
                    break

        return f"""
PARALLEL SUBAGENT TASKS STARTED
===============================
Started {len(task_ids)} tasks in background:
{chr(10).join(f"  - {tid}" for tid in task_ids)}

Use action="check_status" with task_ids={task_ids} to monitor all tasks.
Use action="list_tasks" to see all task statuses.
"""

    async def _check_status_tasks(
        self,
        task_id: Optional[str] = None,
        task_ids: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Check the status of one or more running tasks."""

        ids_to_check = []
        if task_id:
            ids_to_check.append(task_id)
        if task_ids:
            ids_to_check.extend(task_ids)

        if not ids_to_check:
            # Return status of all running tasks
            ids_to_check = [
                tid for tid, tex in self.running_tasks.items()
                if tex.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
            ]

        if not ids_to_check:
            return "No running tasks found."

        statuses = []
        for tid in ids_to_check:
            if tid not in self.running_tasks:
                statuses.append(f"  {tid}: NOT FOUND")
                continue

            tex = self.running_tasks[tid]
            status_info = tex.to_status_dict()

            # Status emoji
            if tex.status == TaskStatus.COMPLETED:
                status_emoji = "✅"
            elif tex.status == TaskStatus.FAILED:
                status_emoji = "❌"
            elif tex.status == TaskStatus.CANCELLED:
                status_emoji = "🚫"
            elif tex.status == TaskStatus.RUNNING:
                status_emoji = "🔄"
            else:
                status_emoji = "⏳"

            duration_str = f"{status_info['duration_seconds']:.1f}s" if status_info['duration_seconds'] else "In progress..."

            statuses.append(f"""
  {status_emoji} {tid}
     Subagent: {tex.subagent_name}
     Status: {tex.status.value}
     Duration: {duration_str}
     Iterations: {tex.iteration_count}
     Tokens: {tex.tokens_used}""")

        return f"""
TASK STATUS CHECK
=================
{''.join(statuses)}
"""

    async def _get_result(
        self,
        task_id: str,
        wait: bool = False,
        timeout: float = 300.0,
        **kwargs
    ) -> str:
        """Get the result of a completed task. Optionally wait for completion."""

        if task_id not in self.running_tasks:
            return f"Error: Task '{task_id}' not found"

        tex = self.running_tasks[task_id]

        # If task is still running and wait=True, wait for it
        if tex.status in (TaskStatus.PENDING, TaskStatus.RUNNING) and wait:
            try:
                await asyncio.wait_for(tex.asyncio_task, timeout=timeout)
            except asyncio.TimeoutError:
                return f"""
TASK STILL RUNNING
==================
Task ID: {task_id}
Status: {tex.status.value}
Message: Task did not complete within {timeout} seconds.
         Use check_status to monitor, or get_result with wait=True and longer timeout.
"""

        # Check if still running (and we didn't wait)
        if tex.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            return f"""
TASK NOT YET COMPLETE
=====================
Task ID: {task_id}
Status: {tex.status.value}
Started: {tex.started_at.isoformat() if tex.started_at else 'N/A'}

Use wait=True to block until completion, or check back later.
"""

        # Task is done - return result
        if tex.status == TaskStatus.COMPLETED:
            result = tex.result
            final_content = result.get("final_message", {}).get("content", "") if result else ""
            duration = (tex.completed_at - tex.started_at).total_seconds() if tex.completed_at and tex.started_at else 0

            return f"""
TASK RESULT: {task_id} ✅
========================
Subagent: {tex.subagent_name}
Status: COMPLETED
Duration: {duration:.1f}s
Iterations: {tex.iteration_count}
Tokens Used: {tex.tokens_used}
Termination Reason: {result.get('termination_reason', 'N/A') if result else 'N/A'}

FINAL OUTPUT:
{final_content if final_content else "No final message content"}
"""

        elif tex.status == TaskStatus.FAILED:
            duration = (tex.completed_at - tex.started_at).total_seconds() if tex.completed_at and tex.started_at else 0
            return f"""
TASK RESULT: {task_id} ❌
========================
Subagent: {tex.subagent_name}
Status: FAILED
Duration: {duration:.1f}s
Error: {tex.error}
"""

        elif tex.status == TaskStatus.CANCELLED:
            duration = (tex.completed_at - tex.started_at).total_seconds() if tex.completed_at and tex.started_at else 0
            return f"""
TASK RESULT: {task_id} 🚫
========================
Subagent: {tex.subagent_name}
Status: CANCELLED
Duration: {duration:.1f}s
"""

        return f"Error: Unknown task status: {tex.status}"

    async def _cancel_task(self, task_id: str, **kwargs) -> str:
        """Cancel a running task."""

        if task_id not in self.running_tasks:
            return f"Error: Task '{task_id}' not found"

        tex = self.running_tasks[task_id]

        if tex.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
            return f"Error: Task '{task_id}' is not running (status: {tex.status.value})"

        if tex.asyncio_task:
            tex.asyncio_task.cancel()
            try:
                await tex.asyncio_task
            except asyncio.CancelledError:
                pass

        tex.status = TaskStatus.CANCELLED
        tex.completed_at = datetime.now()

        return f"""
TASK CANCELLED
==============
Task ID: {task_id}
Subagent: {tex.subagent_name}
Status: CANCELLED
"""

    async def _list_tasks(
        self,
        **kwargs
    ) -> str:
        """List all task executions with their statuses."""

        if not self.running_tasks:
            return "No task executions recorded."

        running = []
        completed = []

        for tid, tex in self.running_tasks.items():
            if tex.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                running.append(tex)
            else:
                completed.append(tex)

        output_parts = []

        if running:
            output_parts.append("RUNNING/PENDING TASKS:")
            for tex in running:
                emoji = "🔄" if tex.status == TaskStatus.RUNNING else "⏳"
                output_parts.append(f"  {emoji} {tex.task_id}: {tex.subagent_name} - {tex.status.value}")

        if completed:
            output_parts.append("\nCOMPLETED TASKS:")
            for tex in sorted(completed, key=lambda x: x.completed_at or datetime.min, reverse=True):
                if tex.status == TaskStatus.COMPLETED:
                    emoji = "✅"
                elif tex.status == TaskStatus.FAILED:
                    emoji = "❌"
                else:
                    emoji = "🚫"
                output_parts.append(f"  {emoji} {tex.task_id}: {tex.subagent_name} - {tex.status.value}")

        completed_count = len([t for t in completed if t.status == TaskStatus.COMPLETED])
        failed_count = len([t for t in completed if t.status == TaskStatus.FAILED])
        cancelled_count = len([t for t in completed if t.status == TaskStatus.CANCELLED])

        return f"""
TASK EXECUTION LIST
===================
Running: {len(running)}
Completed: {completed_count}
Failed: {failed_count}
Cancelled: {cancelled_count}

{chr(10).join(output_parts)}
"""

    async def _store_result_to_filesystem(self, task_id: str, tex: TaskExecution) -> None:
        """Store task result to filesystem for persistence."""
        try:
            task_dir = self.workspace.workspace / "tasks" / task_id
            task_dir.mkdir(parents=True, exist_ok=True)

            # Prepare result data
            result_data = {
                "task_id": task_id,
                "subagent_name": tex.subagent_name,
                "task_input": tex.task_input,
                "status": tex.status.value,
                "started_at": tex.started_at.isoformat() if tex.started_at else None,
                "completed_at": tex.completed_at.isoformat() if tex.completed_at else None,
                "iteration_count": tex.iteration_count,
                "tokens_used": tex.tokens_used,
                "result": tex.result,
                "error": tex.error,
            }

            # Write structured result
            (task_dir / "result.json").write_text(json.dumps(result_data, indent=2, default=str))

            # Write human-readable output
            if tex.result:
                content = tex.result.get("final_message", {}).get("content", "")
                if content:
                    (task_dir / "output.txt").write_text(content)

        except Exception as e:
            # Don't fail the task if filesystem storage fails
            print(f"Warning: Failed to store task result to filesystem: {e}")
