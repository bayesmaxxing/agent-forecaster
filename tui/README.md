# Agent Forecaster TUI

A Terminal User Interface (TUI) for visualizing multi-agent forecaster execution.

## Features (Phase 1)

- **Session Picker**: Browse and select from available log files
- **Agent Hierarchy Tree**: View the parent-child relationships between orchestrator and subagents
- **Event List**: Chronological view of all events with color-coded types
- **Status Indicators**: Visual feedback on agent states (✓ completed, ✗ failed, ⟳ running)
- **Metrics Display**: Token usage and iteration counts per agent

## Installation

Dependencies are already included in the project's `pyproject.toml`:
- `textual>=0.47.0` - Modern TUI framework
- `watchfiles>=0.21.0` - File watching for real-time mode (Phase 4)

Install with:
```bash
uv sync
```

## Usage

### Launch Session Picker (Default)
```bash
uv run python tui_launcher.py
```

This opens an interactive picker showing all available sessions in the `logs/` directory.

### Open Specific Session
```bash
uv run python tui_launcher.py --session multi_agent_20251207_143052
```

### Monitor Live Session (Coming in Phase 4)
```bash
uv run python tui_launcher.py --live multi_agent_20251207_143052
```

## Keyboard Shortcuts

### Global
- `q` - Quit application
- `r` - Reload current session
- `s` - Switch to different session
- `Tab` - Cycle focus between panels

### Session Picker
- `↑/↓` or `j/k` - Navigate sessions
- `Enter` - Select session
- `r` - Refresh session list

### Agent Tree
- `↑/↓` or `j/k` - Navigate agents
- `Enter` - Expand/collapse agent node

### Event List
- `↑/↓` or `j/k` - Navigate events
- `g` - Jump to top
- `G` - Jump to bottom

## Architecture

```
tui/
├── models/         # Data models (SessionModel, AgentNode, Events)
├── widgets/        # Reusable UI widgets (AgentTree, EventList)
├── screens/        # Full screens (SessionPicker, MainScreen)
├── streams/        # Log reading and event processing
├── utils/          # Utilities and formatters
└── app.py          # Main application
```

## Implementation Phases

### ✅ Phase 1: Foundation (Current)
- Basic post-execution log viewer
- Agent hierarchy tree
- Event list
- Session picker

### 🔄 Phase 2: Timeline Visualization (Planned)
- Gantt-style timeline with agent tracks
- Tool call spans visualization
- LLM call markers
- Zoom and pan controls

### 🔄 Phase 3: Rich Event Display (Planned)
- Syntax-highlighted JSON inspector
- Reasoning text formatting
- Filter and search functionality
- Enhanced keyboard shortcuts

### 🔄 Phase 4: Real-Time Mode (Planned)
- Live log tailing
- Auto-scroll timeline
- Pause/resume controls
- Partial tool call handling

### 🔄 Phase 5: Polish & Production (Planned)
- Help system and tutorials
- Export functionality
- Performance optimization
- Configuration files

## Development

To run the TUI during development:
```bash
uv run python tui_launcher.py
```

The TUI uses Textual's CSS-like styling system. Modify `app.py` to customize appearance.

## Troubleshooting

**No sessions found**: Ensure you have `.jsonl` log files in the `logs/` directory. Run `multi_agent.py` to generate logs.

**Import errors**: Make sure dependencies are installed with `uv sync`.

**Display issues**: The TUI requires a terminal with at least 80x24 characters. Some emojis may not render correctly depending on your terminal font.

## Related Files

- `multi_agent.py` - Generates multi-agent session logs
- `agents/utils/logging_util.py` - JSONL logging format
- `log-analyzer/` - Previous Rust-based log analyzer (reference)
