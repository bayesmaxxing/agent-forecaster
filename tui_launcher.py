#!/usr/bin/env python3
"""Entry point for the Agent Forecaster TUI."""

import argparse
import sys
from tui.app import run_tui


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Agent Forecaster TUI - Visualize multi-agent execution"
    )
    parser.add_argument(
        "--session",
        "-s",
        help="Session ID to view (e.g., 'multi_agent_20251207_143052')",
    )
    parser.add_argument(
        "--live",
        "-l",
        help="Monitor live session by ID (real-time mode)",
    )
    parser.add_argument(
        "--logs-dir",
        "-d",
        default="logs",
        help="Directory containing log files (default: logs)",
    )

    args = parser.parse_args()

    # Determine session_id and mode
    session_id = args.session or args.live
    live_mode = bool(args.live)

    # Run the TUI
    try:
        run_tui(session_id=session_id, live_mode=live_mode)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
