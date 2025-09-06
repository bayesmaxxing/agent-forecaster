# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Agent Superforecaster Testbed

## Setup & Development

- **Install dependencies**: `uv sync` 
- **Test single agent**: `uv run python test_agent.py`
- **Environment setup**: Copy and configure `agents/tools/.env` with API keys (minimum: `OPENROUTER_API_KEY`)

## Code Quality & Testing

- **No formal linting/formatting configured** - Project uses basic Python code without specific style enforcement
- **No unit tests** - Only integration testing via `test_agent.py`

## Architecture

This is an experimental AI agent testbed for forecasting, built on OpenRouter for model-agnostic LLM access. The system has two main architectures:

### Single Agent System (`single-agent/`, `test_agent.py`)
- **Core agent**: `agents/agent.py` - Main Agent class with Claude API integration and tool execution loop
- **Tools system**: `agents/tools/` - Modular tool implementations (both native Python and MCP-based)
- **Forecasting MCP**: `agents/tools/forecasting_mcp.py` - MCP server for forecasting API interactions
- **Utils**: `agents/utils/` - Message history management, MCP connections, tool execution

### Multi-Agent System (`multi-agent/agent_system.py`) 
- **Coordinator agent** - Spawns and manages specialized sub-agents
- **Subagent tool** - Creates task-specific agents with appropriate tools and models
- **Shared coordination** - Agents can collaborate on complex forecasting workflows

## Key Components

### Agent (`agents/agent.py`)
- Manages OpenRouter API interactions with configurable models (defaults to anthropic/claude-3.5-sonnet)
- Model-agnostic design supports OpenAI, Anthropic, Google, and other providers via OpenRouter
- Executes tool calls in async loops with automatic context window management
- Supports both local Python tools and external MCP server tools
- Comprehensive logging to `logs/` directory

### Tools Architecture
- **Base tool interface**: `agents/tools/base.py` - Abstract Tool class
- **Native tools**: Think tool for agent reasoning
- **MCP tools**: Forecasting API, Perplexity search via MCP servers
- **Tool execution**: `agents/utils/tool_util.py` - Async tool call handling

### Forecasting Integration
- **MCP server**: Connects to external forecasting API with authentication
- **Tool methods**: get_forecasts, get_forecast_data, update_forecast, query_perplexity
- **Environment config**: OPENROUTER_API_KEY (required), API_URL, BOT_USERNAME, BOT_PASSWORD for forecasting service

## Running the System

The main entry point is `test_agent.py` which configures an autonomous forecasting agent that:
1. Fetches available forecasts via MCP tools
2. Gathers information using Perplexity search
3. Analyzes historical forecast data
4. Makes reasoned predictions with detailed justification

## Dependencies

- **Core**: openai (for OpenRouter), mcp, fastapi, httpx, requests
- **Python version**: >=3.13
- **Package management**: uv (modern pip replacement)