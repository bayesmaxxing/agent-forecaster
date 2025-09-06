"""Base tool definitions for the agent framework."""

try:
    from agents.types import Tool
except ImportError:
    # Fallback for when running as script
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from agents.types import Tool
