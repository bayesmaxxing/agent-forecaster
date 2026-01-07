"""Local execution tools with workspace sandboxing.

Provides Claude Code-style tools that run locally but are restricted
to a specific workspace directory for safety.
"""

import os
import subprocess
import asyncio
from pathlib import Path
from typing import Optional

from .base import Tool


class WorkspaceManager:
    """Manages the workspace directory for sandboxed execution."""

    def __init__(self, workspace_path: Optional[str] = None):
        if workspace_path:
            self.workspace = Path(workspace_path).resolve()
        else:
            # Default to agent_workspace in project root
            self.workspace = Path(__file__).parent.parent.parent / "agent_workspace"

        # Ensure workspace exists with subdirectories
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / "scripts").mkdir(exist_ok=True)
        (self.workspace / "data").mkdir(exist_ok=True)
        (self.workspace / "memory").mkdir(exist_ok=True)

    def resolve_path(self, path: str) -> Path:
        """Resolve a path, ensuring it stays within the workspace.

        Args:
            path: Relative or absolute path

        Returns:
            Resolved absolute path within workspace

        Raises:
            ValueError: If path escapes workspace
        """
        if path.startswith("/"):
            # Absolute path - check if it's within workspace
            resolved = Path(path).resolve()
        else:
            # Relative path - resolve from workspace
            resolved = (self.workspace / path).resolve()

        # Security check: ensure path is within workspace
        try:
            resolved.relative_to(self.workspace)
        except ValueError:
            raise ValueError(
                f"Access denied: path '{path}' is outside the workspace. "
                f"All operations must stay within {self.workspace}"
            )

        return resolved

    def is_safe_command(self, command: str) -> tuple[bool, str]:
        """Check if a command is safe to execute.

        Returns:
            (is_safe, reason) tuple
        """
        # Block commands that could escape workspace
        dangerous_patterns = [
            ("rm -rf /", "Cannot delete root filesystem"),
            ("rm -rf ~", "Cannot delete home directory"),
            ("> /etc/", "Cannot write to system directories"),
            ("sudo", "sudo is not allowed"),
            ("chmod 777 /", "Cannot modify root permissions"),
        ]

        for pattern, reason in dangerous_patterns:
            if pattern in command:
                return False, reason

        return True, ""


# Global workspace instance
_workspace: Optional[WorkspaceManager] = None


def get_workspace() -> WorkspaceManager:
    """Get or create the global workspace manager."""
    global _workspace
    if _workspace is None:
        _workspace = WorkspaceManager()
    return _workspace


def set_workspace(workspace: WorkspaceManager) -> None:
    """Set the global workspace manager."""
    global _workspace
    _workspace = workspace


class LocalBashTool(Tool):
    """Execute bash commands locally, sandboxed to workspace."""

    def __init__(self, workspace: Optional[WorkspaceManager] = None):
        self._workspace = workspace
        super().__init__(
            name="bash",
            description="""Execute a bash command locally in the workspace directory.

Commands are executed with the workspace as the current directory.
You have access to:
- Python 3 and uv package manager (install packages as needed) and run with uv run <command>
- curl, wget for downloading data
- git for version control
- Standard Unix tools (grep, sed, awk, etc.)

The workspace structure:
- scripts/  - Store reusable Python scripts
- data/     - Store downloaded datasets
- memory/   - Store notes and memory files

Network access is available for downloading data and uv installing packages.

IMPORTANT: All file operations should use relative paths from the workspace.
Avoid using absolute paths or navigating outside the workspace.""",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 120)",
                        "default": 120,
                    },
                },
                "required": ["command"],
            },
        )

    async def execute(self, command: str, timeout: int = 120) -> str:
        workspace = self._workspace or get_workspace()

        # Safety check
        is_safe, reason = workspace.is_safe_command(command)
        if not is_safe:
            return f"Command blocked: {reason}"

        try:
            # Run command in workspace directory
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workspace.workspace),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return f"Command timed out after {timeout} seconds"

            output_parts = []

            if stdout:
                output_parts.append(stdout.decode("utf-8", errors="replace"))

            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                if stderr_text.strip():
                    output_parts.append(f"STDERR:\n{stderr_text}")

            if process.returncode != 0:
                output_parts.append(f"\nExit code: {process.returncode}")

            return "\n".join(output_parts) if output_parts else "(no output)"

        except Exception as e:
            return f"Error executing command: {e}"


class LocalReadFileTool(Tool):
    """Read file contents from the workspace."""

    def __init__(self, workspace: Optional[WorkspaceManager] = None):
        self._workspace = workspace
        super().__init__(
            name="read_file",
            description="""Read the contents of a file from the workspace.

Paths should be relative to the workspace directory.
Example: "scripts/fetch_data.py" or "data/results.csv"

The workspace structure:
- scripts/  - Reusable Python scripts
- data/     - Downloaded/generated datasets
- memory/   - Agent notes and memory files""",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to workspace)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max lines to read (default: all)",
                    },
                },
                "required": ["path"],
            },
        )

    async def execute(self, path: str, limit: Optional[int] = None) -> str:
        workspace = self._workspace or get_workspace()

        try:
            resolved = workspace.resolve_path(path)

            if not resolved.exists():
                return f"Error: File not found: {path}"

            if not resolved.is_file():
                return f"Error: Not a file: {path}"

            content = resolved.read_text(encoding="utf-8", errors="replace")

            if limit:
                lines = content.split("\n")
                if len(lines) > limit:
                    content = "\n".join(lines[:limit])
                    content += f"\n\n... ({len(lines) - limit} more lines)"

            return content

        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"Error reading file: {e}"


class LocalWriteFileTool(Tool):
    """Write content to a file in the workspace."""

    def __init__(self, workspace: Optional[WorkspaceManager] = None):
        self._workspace = workspace
        super().__init__(
            name="write_file",
            description="""Write content to a file in the workspace.

Creates the file if it doesn't exist, or overwrites if it does.
Parent directories are created automatically.

Paths should be relative to the workspace directory.
Example: "scripts/fetch_data.py" or "data/results.json"

Use this to:
- Create Python scripts for data collection/analysis
- Save downloaded data
- Write configuration files
- Create reusable utilities""",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to workspace)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                },
                "required": ["path", "content"],
            },
        )

    async def execute(self, path: str, content: str) -> str:
        workspace = self._workspace or get_workspace()

        try:
            resolved = workspace.resolve_path(path)

            # Create parent directories if needed
            resolved.parent.mkdir(parents=True, exist_ok=True)

            resolved.write_text(content, encoding="utf-8")
            return f"Successfully wrote to {path}"

        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"Error writing file: {e}"


class LocalEditFileTool(Tool):
    """Edit an existing file using string replacement."""

    def __init__(self, workspace: Optional[WorkspaceManager] = None):
        self._workspace = workspace
        super().__init__(
            name="edit_file",
            description="""Edit an existing file by replacing a specific string.

Performs an exact string replacement in the file. The old_string must
match exactly (including whitespace and indentation).

For creating new files, use write_file instead.
For reading files before editing, use read_file first.""",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to workspace)",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "The exact string to find and replace",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "The string to replace it with",
                    },
                },
                "required": ["path", "old_string", "new_string"],
            },
        )

    async def execute(self, path: str, old_string: str, new_string: str) -> str:
        workspace = self._workspace or get_workspace()

        try:
            resolved = workspace.resolve_path(path)

            if not resolved.exists():
                return f"Error: File not found: {path}"

            content = resolved.read_text(encoding="utf-8")

            if old_string not in content:
                return "Error: Could not find the specified string. Make sure it matches exactly."

            count = content.count(old_string)
            if count > 1:
                return f"Error: Found {count} occurrences. Please provide a more specific string."

            new_content = content.replace(old_string, new_string, 1)
            resolved.write_text(new_content, encoding="utf-8")

            return f"Successfully edited {path}"

        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"Error editing file: {e}"


class LocalListFilesTool(Tool):
    """List files in a directory."""

    def __init__(self, workspace: Optional[WorkspaceManager] = None):
        self._workspace = workspace
        super().__init__(
            name="list_files",
            description="""List files and directories in the workspace.

Returns a listing of the specified directory path.
Default is the workspace root.""",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path (default: workspace root)",
                        "default": ".",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, path: str = ".") -> str:
        workspace = self._workspace or get_workspace()

        try:
            resolved = workspace.resolve_path(path)

            if not resolved.exists():
                return f"Error: Directory not found: {path}"

            if not resolved.is_dir():
                return f"Error: Not a directory: {path}"

            entries = []
            for item in sorted(resolved.iterdir()):
                if item.is_dir():
                    entries.append(f"  {item.name}/")
                else:
                    size = item.stat().st_size
                    entries.append(f"  {item.name} ({size} bytes)")

            if entries:
                return f"Contents of {path}:\n" + "\n".join(entries)
            else:
                return f"{path} is empty"

        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"Error listing directory: {e}"
