# Agent Superforecaster Testbed

An experimental AI agent testbed for forecasting tasks, built with OpenRouter for model-agnostic LLM access. This project explores different agent architectures (single-agent vs multi-agent) to determine the most effective approach for forecasting workflows.

## Features

- **Model-agnostic design**: Built on OpenRouter API supporting OpenAI, Anthropic, Google, and X.AI models
- **Single-agent system**: Autonomous agent with direct tool access for iterative forecasting workflows
- **Multi-agent system**: Orchestrator-based architecture with specialized sub-agents and shared memory for complex task coordination
- **Native forecasting tools**: Direct API integration with forecasting platform, Perplexity search, and thinking tools
- **Comprehensive logging**: All agent activity logged to timestamped files for analysis
- **Interactive log analyzer**: Terminal UI for visualizing agent execution, tool calls, and token usage in real-time

## Quick Start

### Prerequisites
- Python ≥3.13
- uv package manager
- OpenRouter API key
- Rust and Cargo (optional, for log analyzer)

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

### Analyzing Logs

The project includes an interactive terminal UI for analyzing agent logs built with Rust and ratatui:

```bash
# Build the log analyzer (requires Rust/Cargo)
cd log-analyzer
cargo build --release

# Run the log analyzer on a log file
cargo run --release ../logs/agent_YYYYMMDD_HHMMSS.jsonl
```

**Features:**
- **Timeline view**: Chronological display of all agent events (LLM calls, tool executions, results)
- **Tool statistics**: Real-time tracking of tool usage, success rates, and errors
- **Token usage tracking**: Monitor token consumption per agent and across the entire session
- **Event filtering**: Filter by event type (LLM responses, tool calls, tool results)
- **Vim-style navigation**:
  - `j`/`k` or arrow keys: Navigate entries
  - `g`/`G`: Jump to first/last entry
  - `d`: Toggle detailed view
  - `f`: Cycle through event filters
  - `[count]j/k`: Navigate by count (e.g., `10j` moves down 10 entries)
  - `q`: Quit

The log analyzer is particularly useful for debugging multi-agent workflows, understanding token usage patterns, and identifying bottlenecks in agent execution.

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

log-analyzer/            # Rust-based TUI for log analysis
├── src/
│   ├── main.rs          # Application entry point and event loop
│   ├── models.rs        # Log entry data structures
│   └── ui.rs            # Terminal UI rendering
└── Cargo.toml           # Rust dependencies

logs/                    # Timestamped JSONL log files from agent runs
```

## Development

See [CLAUDE.md](CLAUDE.md) for detailed architecture documentation and development guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
