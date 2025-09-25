# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Agent Superforecaster Testbed

## Setup & Development

- **Install dependencies**: `uv sync`
- **Test single agent**: `uv run python single_agent.py` (main single-agent entry point)
- **Test with specific models**: `uv run python single_agent.py -m opus|gpt-5|grok|gemini -v true`
- **Test multi-agent**: `uv run python multi_agent.py` (main multi-agent entry point)
- **Environment setup**: Set `OPENROUTER_API_KEY` environment variable (required)
- **Optional env vars**: `API_URL`, `BOT_USERNAME`, `BOT_PASSWORD` for forecasting service integration

## Code Quality & Testing

- **No formal linting/formatting configured** - Project uses basic Python code without specific style enforcement
- **No unit tests** - Only integration testing via entry point scripts
- **Logging**: All agent activity logged to `logs/` directory with timestamps

## Architecture

This is an experimental AI agent testbed for forecasting, built on OpenRouter for model-agnostic LLM access. The system has two main architectures:

### Single Agent System (`single_agent.py`)
- **Core agent**: `agents/agent.py` - Main Agent class with OpenRouter API integration and async tool execution loop
- **Tools system**: `agents/tools/` - Modular tool implementations with base class pattern
- **Native tools**: Think tool, Perplexity search, direct forecasting API tools
- **Utils**: `agents/utils/` - Message history with context window management, async tool execution
- **Model support**: Configurable via ModelConfig for OpenAI, Anthropic, Google, X.AI models through OpenRouter

### Multi-Agent System (`multi_agent.py`)
- **Orchestrator agent** - Coordinator that spawns specialized sub-agents via SubagentManagerTool
- **Subagent tool** (`agents/tools/subagent_tool.py`) - Creates, runs, and manages task-specific agents
- **Dynamic agent creation** - Sub-agents configured with specific tools, models, and system prompts
- **Shared memory system** - Agents coordinate via SharedMemoryTool and SharedMemoryManagerTool for cross-agent communication

## Key Components

### Agent (`agents/agent.py`)
- **Core class**: Manages OpenRouter API interactions with configurable models (defaults to openai/gpt-5)
- **Model-agnostic design**: Supports OpenAI, Anthropic, Google, X.AI providers via OpenRouter base URL
- **Async execution**: Tool calls processed in async loops with automatic context window management
- **Message history**: `MessageHistory` class handles context truncation and API formatting
- **Logging**: Comprehensive logging to timestamped files in `logs/` directory

### Tools Architecture
- **Base tool interface**: `agents/tools/base.py` - Abstract Tool class with name, description, input_schema
- **Native Python tools**: Think tool, forecasting API tools, Perplexity search tool
- **Tool execution**: `agents/utils/tool_util.py` - Async tool call handling with error management
- **Tool registration**: Tools passed to Agent constructor and available during execution loop

### Key Tool Implementation Pattern
```python
class ExampleTool(Tool):
    def __init__(self):
        super().__init__(
            name="tool_name",
            description="Tool description",
            input_schema={...}  # JSON schema for parameters
        )

    async def execute(self, **kwargs) -> str:
        # Tool implementation
        return result_string
```

### Agent Execution Flow
1. **Initialization**: Agent configured with system prompt, tools, model config
2. **Message loop**: `_agent_loop()` processes user input → API call → tool calls → repeat until no tool calls
3. **Tool execution**: Parallel async execution of tool calls via `execute_tools()`
4. **Context management**: History automatically truncated when approaching context window limits

## Running the System

### Single Agent
- **Entry point**: `single_agent.py` - Loads system prompt from `prompt.md`
- **Autonomous mode**: Agent runs with "Go ahead and forecast!" input and continues until completion
- **Tools available**: Think, forecasting API tools (GetForecasts, GetForecastData, GetForecastPoints, UpdateForecast), QueryPerplexity, RequestFeedback

### Multi-Agent
- **Entry point**: `multi_agent.py` - Orchestrator spawns and manages sub-agents
- **Subagent management**: Create, run, delete specialized agents with specific tool sets via SubagentManagerTool
- **Shared memory**: Cross-agent coordination through shared memory system for task collaboration
- **Workflow**: Orchestrator breaks down tasks, assigns to specialized sub-agents, synthesizes results

## Dependencies

- **Core**: openai (for OpenRouter API), mcp, fastapi, requests
- **Python version**: >=3.13 (specified in pyproject.toml)
- **Package management**: uv (modern pip replacement)
- **Key patterns**: Async/await throughout, dataclasses for configuration, comprehensive logging

## Development Notes

- **Code style**: Follow existing patterns in `agents/` directory
- **New tools**: Inherit from `agents.tools.base.Tool` and implement `execute()` method
- **Agent configuration**: Use `ModelConfig` dataclass for model parameters
- **Error handling**: Tools should return error strings rather than raising exceptions
- **Imports**: Use relative imports within agents package, absolute for external dependencies