# Agent Superforecaster Testbed

An experimental AI agent testbed for forecasting tasks, built with OpenRouter for model-agnostic LLM access. This project explores different agent architectures (single-agent vs multi-agent) to determine the most effective approach for forecasting workflows.

## Features

- **Model-agnostic design**: Built on OpenRouter API supporting OpenAI, Anthropic, Google, and X.AI models
- **Single-agent system**: Autonomous agent with direct tool access for iterative forecasting workflows
- **Multi-agent system**: Orchestrator-based architecture with specialized sub-agents and shared memory for complex task coordination
- **Native forecasting tools**: Direct API integration with forecasting platform, Perplexity search, and thinking tools
- **Comprehensive logging**: All agent activity logged to timestamped files for analysis

## Quick Start

### Prerequisites
- Python ≥3.13
- uv package manager
- OpenRouter API key

### Setup

```bash
# Install dependencies
uv sync

# Set required environment variable
export OPENROUTER_API_KEY=your_key_here

# Optional: Configure forecasting service
export API_URL=your_api_url
export BOT_USERNAME=your_username
export BOT_PASSWORD=your_password
```

### Running the Agents

```bash
# Test single-agent system
uv run python single_agent.py

# Test with specific models
uv run python single_agent.py -m opus|gpt-5|grok|gemini -v true

# Test multi-agent system
uv run python multi_agent.py
```

## Architecture

### Single-Agent System
- **Entry point**: `single_agent.py`
- **Core agent**: `agents/agent.py` - OpenRouter API integration with async tool execution
- **Tools**: Think tool, forecasting API tools (GetForecasts, GetForecastData, UpdateForecast), QueryPerplexity
- **Flow**: Autonomous execution with iterative tool use until task completion

### Multi-Agent System
- **Entry point**: `multi_agent.py`
- **Orchestrator**: Coordinates task decomposition and sub-agent spawning
- **Sub-agents**: Task-specific agents with specialized tool sets
- **Coordination**: Shared memory system for cross-agent communication

## Project Structure

```
agents/
├── agent.py              # Core Agent class with OpenRouter integration
├── tools/
│   ├── base.py          # Abstract Tool base class
│   ├── subagent_tool.py # Sub-agent management
│   └── ...              # Native tool implementations
└── utils/
    ├── message_history.py   # Context window management
    └── tool_util.py         # Async tool execution
```

## Development

See [CLAUDE.md](CLAUDE.md) for detailed architecture documentation and development guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
