"""Tool for subagents to report their results back to the coordinator."""

from .base import Tool


class ReportResultsTool(Tool):
    """Tool for subagents to report their findings and mark task completion."""

    def __init__(self):
        super().__init__(
            name="report_results",
            description="Report findings and results back to the coordinator agent. Use this when task is complete.",
            input_schema={
                "type": "object",
                "properties": {
                    "task_status": {
                        "type": "string",
                        "enum": ["completed", "partially_completed", "failed"],
                        "description": "Status of the assigned task"
                    },
                    "findings": {
                        "type": "string",
                        "description": "Key findings, results, or data discovered during task execution"
                    },
                    "recommendations": {
                        "type": "string",
                        "description": "Recommendations for next steps or additional actions needed"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "Confidence level in the findings (0-100)"
                    },
                    "additional_data": {
                        "type": "object",
                        "description": "Any structured data or metadata to pass back to coordinator",
                        "additionalProperties": True
                    }
                },
                "required": ["task_status", "findings"]
            }
        )

    async def execute(
        self,
        task_status: str,
        findings: str,
        recommendations: str = "",
        confidence: float = 80.0,
        additional_data: dict = None
    ) -> str:
        """Execute the reporting tool."""

        report = {
            "task_status": task_status,
            "findings": findings,
            "recommendations": recommendations,
            "confidence": confidence,
            "additional_data": additional_data or {}
        }

        # Format the report for the coordinator
        formatted_report = f"""
SUBAGENT TASK REPORT
====================
Status: {task_status.upper()}
Confidence: {confidence}%

FINDINGS:
{findings}

RECOMMENDATIONS:
{recommendations if recommendations else "None"}

ADDITIONAL DATA:
{additional_data if additional_data else "None"}
"""

        # Store report in shared memory for coordinator access
        try:
            from ..utils.shared_memory import get_shared_memory
            shared_memory = get_shared_memory()

            # Store the full report
            shared_memory.store(
                agent_name="system",  # Mark as system-generated
                task_id="multi_agent_session",
                category="coordination",
                title=f"Task Report - Status: {task_status}",
                content=formatted_report,
                metadata={
                    "report_type": "task_completion",
                    "task_status": task_status,
                    "confidence": confidence,
                    "structured_data": report
                },
                tags=["report", "task_completion", task_status]
            )

        except Exception as e:
            # Don't fail the report if memory storage fails
            print(f"Warning: Failed to store report in shared memory: {e}")

        return f"✅ Task report submitted and stored in shared memory.\n{formatted_report}"


class RequestGuidanceTool(Tool):
    """Tool for subagents to request guidance or clarification from the coordinator."""

    def __init__(self):
        super().__init__(
            name="request_guidance",
            description="Request guidance, clarification, or additional instructions from the coordinator agent.",
            input_schema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The specific question or issue that needs clarification"
                    },
                    "context": {
                        "type": "string",
                        "description": "Context about what you've tried so far and why guidance is needed"
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Urgency level of the guidance request"
                    }
                },
                "required": ["question", "context"]
            }
        )

    async def execute(
        self,
        question: str,
        context: str,
        urgency: str = "medium"
    ) -> str:
        """Execute the guidance request tool."""

        guidance_request = f"""
GUIDANCE REQUEST ({urgency.upper()} PRIORITY)
=====================================

QUESTION:
{question}

CONTEXT:
{context}

Please provide guidance on how to proceed.
"""

        # Store guidance request in shared memory for coordinator access
        try:
            from ..utils.shared_memory import get_shared_memory
            shared_memory = get_shared_memory()

            shared_memory.store(
                agent_name="system",
                task_id="multi_agent_session",
                category="coordination",
                title=f"Guidance Request - {urgency.upper()} Priority",
                content=guidance_request,
                metadata={
                    "request_type": "guidance",
                    "urgency": urgency,
                    "question": question,
                    "context": context
                },
                tags=["guidance_request", urgency, "coordination"]
            )

        except Exception as e:
            print(f"Warning: Failed to store guidance request in shared memory: {e}")

        return f"✅ Guidance request submitted and stored in shared memory.\n{guidance_request}"