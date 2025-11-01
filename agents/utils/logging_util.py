"""Centralized logging utility for the forecasting agent system."""

import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class AgentType(Enum):
    """Agent type for logging hierarchy."""
    ORCHESTRATOR = "orchestrator"
    SUBAGENT = "subagent"
    TOOL = "tool"


class LogLevel(Enum):
    """Custom log levels."""
    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class SessionLogger:
    """Session-aware logger with JSON Lines output."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.setup_logging()

    def setup_logging(self):
        """Set up logging with JSON Lines format for file, human-readable for console."""
        # Create logs directory
        logs_dir = "logs"
        os.makedirs(logs_dir, exist_ok=True)

        # Session-based log file
        log_filename = os.path.join(logs_dir, f'{self.session_id}.jsonl')

        # Remove existing handlers
        logging.root.handlers = []

        # JSON formatter for file
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                # If record has json_data, use it directly
                if hasattr(record, 'json_data'):
                    return json.dumps(record.json_data)
                # Otherwise create basic log entry
                return json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "level": record.levelname.lower(),
                    "message": record.getMessage()
                })

        # Human-readable formatter for console
        class ConsoleFormatter(logging.Formatter):
            def format(self, record):
                if hasattr(record, 'console_msg'):
                    return record.console_msg
                return super().format(record)

        # File handler with JSON
        file_handler = logging.FileHandler(log_filename)
        file_handler.setFormatter(JSONFormatter())

        # Console handler with human-readable format
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ConsoleFormatter())

        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            handlers=[file_handler, console_handler],
            force=True
        )

        self.logger = logging.getLogger(f'Session-{self.session_id}')

        # Log session start
        self.log_session_start()

    def _log(self,
             event_type: str,
             level: LogLevel,
             agent_name: Optional[str] = None,
             agent_type: Optional[AgentType] = None,
             console_msg: Optional[str] = None,
             **data):
        """Internal method to emit structured JSON logs."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "event_type": event_type,
            "level": level.value,
        }

        if agent_name:
            log_entry["agent_name"] = agent_name
        if agent_type:
            log_entry["agent_type"] = agent_type.value

        if data:
            log_entry["data"] = data

        # Create log record with both JSON and console format
        record = logging.LogRecord(
            name=self.logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None
        )
        record.json_data = log_entry
        record.console_msg = console_msg or self._format_console(event_type, level, agent_name, agent_type, data)

        self.logger.handle(record)

    def _format_console(self,
                        event_type: str,
                        level: LogLevel,
                        agent_name: Optional[str],
                        agent_type: Optional[AgentType],
                        data: Dict[str, Any]) -> str:
        """Format a human-readable console message from structured data."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        level_str = f"[{level.value.upper()}]"

        if event_type == "session_start":
            border = "=" * 60
            return f"\n{border}\nNEW FORECASTING SESSION: {self.session_id}\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{border}"
        elif event_type == "session_end":
            border = "=" * 60
            reason = data.get('reason', 'Completed')
            return f"\n{border}\nSESSION ENDED: {reason}\nEnded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{border}"
        elif event_type == "agent_action":
            agent_prefix = f"[{agent_type.value.upper()}]" if agent_type else ""
            name_str = f"[{agent_name}]" if agent_name else ""
            action = data.get('action', '')
            details = data.get('details', '')
            indent = data.get('indent', 0)
            indent_str = "  " * indent
            prefix = "├─" if indent > 0 else ""
            msg = f"{indent_str}{prefix} {agent_prefix} {name_str} {action}"
            if details:
                msg += f" | {details}"
            return f"{timestamp} | {level_str} {msg}"
        elif event_type == "llm_response":
            model = data.get('model', 'unknown')
            tokens = data.get('tokens', {}).get('total')
            token_str = f" | {tokens:,} tokens" if tokens else ""
            return f"{timestamp} | {level_str} [LLM] {model}{token_str}"
        elif event_type == "tool_call":
            tool_name = data.get('tool_name', 'unknown')
            params = data.get('params', {})
            result = data.get('result_summary', '')
            indent = data.get('indent', 1)
            indent_str = "  " * indent
            prefix = "├─"

            param_str = ""
            if params:
                key_params = [f"{k}: {v}" for k, v in list(params.items())[:3]]
                param_str = f"({', '.join(key_params)})"

            msg = f"{indent_str}{prefix} [TOOL] → {tool_name}{param_str}"
            if result:
                msg += f" ✓"
            return f"{timestamp} | {level_str} {msg}"
        elif event_type == "tool_result":
            tool_name = data.get('tool_name', 'unknown')
            result_content = data.get('result_content', '')
            is_error = data.get('is_error', False)
            indent = data.get('indent', 1)
            indent_str = "  " * indent
            prefix = "├─"

            # Truncate long results for console display
            display_content = result_content
            if len(display_content) > 100:
                display_content = display_content[:97] + "..."

            status = "✗" if is_error else "✓"
            msg = f"{indent_str}{prefix} [TOOL] {status} {tool_name} → {display_content}"
            return f"{timestamp} | {level_str} {msg}"
        elif event_type == "cycle":
            cycle_num = data.get('cycle_number', 0)
            action = data.get('action', 'Starting')
            border = "-" * 40
            return f"\n{border}\nCYCLE {cycle_num} | {action}\n{border}"
        elif event_type == "execution_summary":
            status = "SUCCESS" if data.get('success') else "INCOMPLETE"
            iterations = data.get('iterations', 0)
            tokens = data.get('tokens', 0)
            reason = data.get('termination_reason', '')
            status_prefix = "[SUCCESS]" if data.get('success') else "[INCOMPLETE]"
            indent = data.get('indent', 1)
            indent_str = "  " * indent
            prefix = "├─" if indent > 0 else ""
            msg = f"{indent_str}{prefix} {status_prefix} {status} | {iterations} iterations | {tokens:,} tokens | {reason}"
            return f"{timestamp} | {level_str} {msg}"
        elif event_type == "subagent_lifecycle":
            action = data.get('action', '')
            details = data.get('details', '')
            indent = data.get('indent', 1)
            indent_str = "  " * indent
            prefix = "├─" if indent > 0 else ""
            msg = f"{indent_str}{prefix} [SUBAGENT] [{agent_name}] {action}"
            if details:
                msg += f" | {details}"
            return f"{timestamp} | {level_str} {msg}"
        elif event_type == "error":
            error = data.get('error', '')
            context = data.get('context')
            msg = f"[{agent_name}] Error: {error}"
            if context:
                msg += f" | Context: {context}"
            return f"{timestamp} | {level_str} {msg}"
        elif event_type == "text_block":
            title = data.get('title', '')
            lines = data.get('lines', [])
            truncated = data.get('truncated', False)
            total_lines = data.get('total_lines', 0)
            indent = data.get('indent', 1)
            indent_str = "  " * indent
            prefix = "├─" if indent > 0 else ""
            result = f"{timestamp} | {level_str} {indent_str}{prefix} {title}\n"
            content_indent = "  " * (indent + 1)
            for line in lines:
                result += f"         | {content_indent}│ {line}\n"
            if truncated:
                result += f"         | {content_indent}│ ... ({total_lines - len(lines)} more lines truncated)\n"
            return result.rstrip()
        elif event_type == "context_snapshot":
            turn = data.get('turn_number', 0)
            msg_count = data.get('message_count', 0)
            tokens = data.get('total_tokens')
            token_str = f" | {tokens:,} tokens" if tokens else ""
            return f"{timestamp} | {level_str} [CONTEXT] Turn {turn} | {msg_count} messages{token_str}"
        elif event_type == "debug":
            msg = data.get('message', '')
            return f"{timestamp} | {level_str} {msg}"
        else:
            return f"{timestamp} | {level_str} {event_type}: {data}"

    def log_session_start(self):
        """Log the start of a new session."""
        self._log(
            event_type="session_start",
            level=LogLevel.INFO,
            started_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

    def log_agent_action(self,
                        agent_name: str,
                        action: str,
                        agent_type: AgentType = AgentType.ORCHESTRATOR,
                        level: LogLevel = LogLevel.INFO,
                        details: Optional[str] = None,
                        ):
        """Log an agent action with visual hierarchy."""
        self._log(
            event_type="agent_action",
            level=level,
            agent_name=agent_name,
            agent_type=agent_type,
            action=action,
            details=details,
        )

    def log_tool_call(self,
                     agent_name: str,
                     tool_name: str,
                     params: Optional[Dict[str, Any]] = None,
                     result_summary: Optional[str] = None,
                    ):
        """Log a tool call with parameters summary."""
        self._log(
            event_type="tool_call",
            level=LogLevel.INFO,
            agent_name=agent_name,
            agent_type=AgentType.TOOL,
            tool_name=tool_name,
            params=params or {},
            result_summary=result_summary,
        )

    def log_tool_result(self,
                       agent_name: str,
                       tool_name: str,
                       result_content: str,
                       is_error: bool = False,
                       tool_call_id: Optional[str] = None):
        """Log a tool execution result."""
        level = LogLevel.ERROR if is_error else LogLevel.SUCCESS
        self._log(
            event_type="tool_result",
            level=level,
            agent_name=agent_name,
            agent_type=AgentType.TOOL,
            tool_name=tool_name,
            result_content=result_content,
            is_error=is_error,
            tool_call_id=tool_call_id,
        )

    def log_subagent_lifecycle(self,
                              subagent_name: str,
                              action: str,
                              details: Optional[str] = None):
        """Log subagent creation, execution, completion."""
        level = LogLevel.SUCCESS if action in ["Created", "Completed"] else LogLevel.INFO
        self._log(
            event_type="subagent_lifecycle",
            level=level,
            agent_name=subagent_name,
            agent_type=AgentType.SUBAGENT,
            action=action,
            details=details,
        )

    def log_execution_summary(self,
                            agent_name: str,
                            iterations: int,
                            tokens: int,
                            success: bool,
                            termination_reason: str):
        """Log a concise execution summary."""
        level = LogLevel.SUCCESS if success else LogLevel.WARNING
        self._log(
            event_type="execution_summary",
            level=level,
            agent_name=agent_name,
            agent_type=AgentType.SUBAGENT,
            iterations=iterations,
            tokens=tokens,
            success=success,
            termination_reason=termination_reason,
        )

    def log_cycle(self, cycle_number: int, action: str = "Starting"):
        """Log cycle information for multi-agent sessions."""
        self._log(
            event_type="cycle",
            level=LogLevel.INFO,
            cycle_number=cycle_number,
            action=action
        )

    def log_session_end(self, reason: str = "Completed"):
        """Log the end of a session."""
        self._log(
            event_type="session_end",
            level=LogLevel.INFO,
            reason=reason,
            ended_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

    def log_error(self, agent_name: str, error: str, context: Optional[str] = None):
        """Log errors with context."""
        self._log(
            event_type="error",
            level=LogLevel.ERROR,
            agent_name=agent_name,
            error=error,
            context=context
        )

    def log_llm_response(self,
                        agent_name: str,
                        content: Optional[str] = None,
                        reasoning: Optional[str] = None,
                        model: str = "unknown",
                        tokens: Optional[int] = None,
                        prompt_tokens: Optional[int] = None,
                        completion_tokens: Optional[int] = None,
                        indent: int = 0):
        """Log LLM response content and reasoning."""
        token_data = {}
        if tokens:
            token_data['total'] = tokens
        if prompt_tokens:
            token_data['prompt'] = prompt_tokens
        if completion_tokens:
            token_data['completion'] = completion_tokens

        self._log(
            event_type="llm_response",
            level=LogLevel.INFO,
            agent_name=agent_name,
            model=model,
            tokens=token_data,
            content=content,
            reasoning=reasoning,
        )

    def log_text_block(self,
                      title: str,
                      content: str,
                      max_lines: int = 100):
        """Log a block of text with proper formatting and truncation."""
        lines = content.split('\n')
        truncated = len(lines) > max_lines
        if truncated:
            lines = lines[:max_lines]

        self._log(
            event_type="text_block",
            level=LogLevel.INFO,
            title=title,
            content=content,
            lines=lines,
            truncated=truncated,
            total_lines=len(content.split('\n')),   
        )

    def log_raw_debug(self, message: str, level: int = logging.DEBUG):
        """Log raw debug information (API responses, etc.) at debug level."""
        if logging.root.level <= level:
            self._log(
                event_type="debug",
                level=LogLevel.DEBUG,
                message=message
            )

    def log_context_snapshot(self,
                            agent_name: str,
                            messages: list,
                            turn_number: int,
                            total_tokens: Optional[int] = None):
        """Log a snapshot of the entire conversation context at a specific turn."""
        self._log(
            event_type="context_snapshot",
            level=LogLevel.DEBUG,
            agent_name=agent_name,
            turn_number=turn_number,
            messages=messages,
            total_tokens=total_tokens,
            message_count=len(messages)
        )


# Global session logger instance
_session_logger: Optional[SessionLogger] = None


def get_session_logger() -> SessionLogger:
    """Get or create the global session logger."""
    global _session_logger
    if _session_logger is None:
        _session_logger = SessionLogger()
    return _session_logger


def set_session_logger(session_id: str) -> SessionLogger:
    """Set a new session logger with specific ID."""
    global _session_logger
    _session_logger = SessionLogger(session_id)
    return _session_logger


def cleanup_session_logger():
    """Clean up the global session logger."""
    global _session_logger
    if _session_logger:
        _session_logger.log_session_end()
    _session_logger = None