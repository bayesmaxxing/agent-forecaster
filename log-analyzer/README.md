# Log Analyzer - Interactive TUI

A Rust-based Terminal User Interface (TUI) for analyzing JSONL logs from forecasting agents. Provides real-time visual analysis with timeline views, statistics, and detailed event inspection.

## Building

```bash
cargo build --release
```

## Usage

```bash
# Run the TUI with a log file
cargo run --release -- logs/session_20250101_120000.jsonl

# Or use the compiled binary
./target/release/log-analyzer logs/session_20250101_120000.jsonl
```

## Features

### 📊 **Live Statistics Panel**
- Total tokens used across all LLM calls
- Number of LLM API calls
- Top 3 tools by usage with success/error counts
- Total events in session

### 📜 **Interactive Timeline**
- Scrollable chronological view of all events
- Color-coded event types with icons:
  - 🤖 LLM Responses (Blue)
  - 🔧 Tool Calls (Green)
  - 📦 Tool Results (Cyan)
  - ⚡ Agent Actions (Yellow)
  - 📊 Execution Summaries (Magenta)
  - 🚀 Session Start (Green)
  - 🏁 Session End (Red)
- Agent name displayed for each event
- Event filtering capabilities

### 🔍 **Details Panel**
- Press `d` to toggle detailed view
- Shows full content for selected event:
  - **LLM Responses**: Model, tokens (total/prompt/completion), reasoning, content
  - **Tool Calls**: Tool name, all parameters with values
  - **Tool Results**: Success/error status, full result content
  - **Raw Data**: JSON view for other event types

## Keyboard Controls

| Key | Action |
|-----|--------|
| `q` | Quit the application |
| `j` / `↓` | Move down in timeline |
| `k` / `↑` | Move up in timeline |
| `[count]j/k` | Vim-style: Move N lines (e.g., `20j` moves 20 lines down) |
| `d` | Toggle details panel |
| `f` | Cycle through event filters (all → llm_response → tool_call → tool_result → all) |
| `g` | Jump to top of timeline |
| `G` | Jump to bottom of timeline |
| `Esc` | Clear count prefix |

## Event Filtering

Press `f` to cycle through filters:
1. **All Events** - Shows everything
2. **LLM Responses** - Only AI model outputs
3. **Tool Calls** - Only tool invocations
4. **Tool Results** - Only tool execution results

The current filter is shown in the timeline title.

## Installation

For easier access, install the binary globally:

```bash
cargo install --path .
```

Then use it directly:

```bash
log-analyzer logs/session.jsonl
```

### Shell Alias

Add to your `.zshrc` or `.bashrc`:

```bash
alias analyze='log-analyzer'
```

Then:

```bash
analyze logs/latest.jsonl
```

## Quick Start

1. Run your forecasting agent to generate logs
2. Launch the analyzer: `cargo run --release -- logs/session_YYYYMMDD_HHMMSS.jsonl`
3. Use `j/k` to navigate through events
4. Press `d` to see full details of selected event
5. Press `f` to filter by event type
6. Press `q` to exit

## Example Workflow

```bash
# Run your agent
uv run python single_agent.py -v true

# Analyze the latest log
cargo run --release -- $(ls -t logs/*.jsonl | head -1)

# Navigate with j/k, press d to see LLM reasoning chains
# Press f to filter to only LLM responses
# View token usage and tool statistics in the top panel
```

## Architecture

- **Main Loop**: Event-driven with crossterm for terminal handling
- **UI Rendering**: Ratatui for beautiful terminal UI components
- **Data Models**: Strongly-typed parsing of JSONL log entries
- **State Management**: Single AppState with selection, scrolling, and view modes
