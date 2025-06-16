from typing import List, Optional
from dataclasses import dataclass
from agents.agent import Agent, ModelConfig
from agents.tools import Tool
from agents.tools import QueryPerplexityTool, GetForecastsTool, GetForecastDataTool, GetForecastPointsTool, UpdateForecastTool

@dataclass
class SubagentConfig:
    name: str
    system_prompt: str
    tools: List[Tool]
    model_config: ModelConfig

class SubagentManagerTool(Tool):
    def __init__(self, subagents: dict[str, Agent]):
        super().__init__(
            name="subagent_manager",
            description="Manage subagents with specific capabilities and goals",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "run", "delete"],
                        "description": "The action to perform on subagents."
                    },
                    "name": {
                        "type": "string",
                        "description": "Unique name for the subagent (required for create, run and delete actions)"
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "System prompt defining the subagent's role and goals (required for create action)"
                    },
                    "tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tool names this subagent should have access to (required for create action)"
                    },
                    "model": {
                        "type": "string",
                        "description": "Model to use for this subagent (haiku, sonnet, sonnet-4, or opus-4) (required for create action)",
                        "enum": ["claude-haiku-20240307", "claude-sonnet-3-5-20241022", "claude-sonnet-4-20250514", "claude-opus-4-20250514"]
                    }
                },
                "required": ["action"],
            }
        )

        self.subagents = subagents
        self.available_tools = {
            "query_perplexity": QueryPerplexityTool(),
            "get_forecasts": GetForecastsTool(),
            "get_forecast_data": GetForecastDataTool(),
            "get_forecast_points": GetForecastPointsTool(),
            "update_forecast": UpdateForecastTool(),
            "memory": SharedMemoryTool(), #TODO: create a shared memory tool that subagents can use to share information with the orchestrator and the other subagents.
        }

    async def execute(self, action: str, **kwargs) -> str:
        if action == "create": 
            return await self._create_subagent(**kwargs)
        elif action == "run":
            return await self._run_subagent(**kwargs)
        elif action == "delete":
            return await self._delete_subagent(**kwargs)
        elif action == "list":
            return await self._list_subagents()
        else:
            return f"Error: Invalid action '{action}'"
        
    async def _create_subagent(self, name: str, system_prompt: str, tools: List[Tool], model: str) -> str:
        if name in self.subagents:
            return f"Error: Subagent '{name}' already exists"
        
        # Get the requested tools
        agent_tools = []
        for tool_name in tools:
            if tool_name in self.available_tools:
                agent_tools.append(self.available_tools[tool_name])
            else:
                return f"Error: Tool '{tool_name}' not available"
            
        if "memory" not in agent_tools:
            agent_tools.append(self.available_tools["memory"])
            
        self.subagents[name] = Agent(
            name=name,
            system=system_prompt,
            tools=agent_tools,
            config=ModelConfig(
                model=model,
                max_tokens=4096,
                temperature=1.0 # perhaps this could be made into a parameter for the orchestrator agent as well
            )
        )
        return f"Successfully created subagent '{name}' with {len(tools)} tools"
        
    async def _run_subagent(self, name: str) -> str:
        if name not in self.subagents:
            return f"Error: Subagent '{name}' does not exist"
        
        try:
            await self.subagents[name].run_async(f"Run with the task you have been given. Return the relevant information using the memory tool.")
            return f"Successfully ran subagent '{name}'"
        except Exception as e:
            return f"Error: Failed to run subagent '{name}': {e}"
        
    def _delete_subagent(self, name: str) -> str:
        if name not in self.subagents:
            return f"Error: Subagent '{name}' does not exist"
        del self.subagents[name]
        return f"Successfully deleted subagent '{name}'"
    
    def _list_subagents(self) -> str:
        if not self.subagents:
            return "No subagents exist"
        
        return "Existing subagents:\n" + "\n".join(
            f"- {name}: {agent.system[:100]}..." 
            for name, agent in self.subagents.items()
        )