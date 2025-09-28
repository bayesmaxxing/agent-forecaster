"""Centralized logging utility for the forecasting agent system."""

import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class AgentType(Enum):
    """Agent type for logging hierarchy."""
    ORCHESTRATOR = "[ORCH]"
    SUBAGENT = "[SUB]"
    TOOL = "[TOOL]"


class LogLevel(Enum):
    """Custom log levels with text prefixes for better readability."""
    DEBUG = "[DEBUG]"
    INFO = "[INFO]"
    SUCCESS = "[SUCCESS]"
    WARNING = "[WARN]"
    ERROR = "[ERROR]"


class SessionLogger:
    """Session-aware logger with visual hierarchy and structured output."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.setup_logging()

    def setup_logging(self):
        """Set up logging with session-based file and improved formatting."""
        # Create logs directory
        logs_dir = "logs"
        os.makedirs(logs_dir, exist_ok=True)

        # Session-based log file
        log_filename = os.path.join(logs_dir, f'{self.session_id}.log')

        # Create custom formatter
        class CustomFormatter(logging.Formatter):
            def format(self, record):
                # Use custom formatting if present, otherwise default
                if hasattr(record, 'custom_format') and record.custom_format:
                    return record.custom_format
                return super().format(record)

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(message)s',
            datefmt='%H:%M:%S',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ],
            force=True  # Override existing config
        )

        # Apply custom formatter
        for handler in logging.root.handlers:
            handler.setFormatter(CustomFormatter())

        self.logger = logging.getLogger(f'Session-{self.session_id}')

        # Log session start
        self.log_session_start()

    def log_session_start(self):
        """Log the start of a new session."""
        border = "=" * 60
        self.logger.info(f"\n{border}")
        self.logger.info(f"NEW FORECASTING SESSION: {self.session_id}")
        self.logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{border}")

    def log_agent_action(self,
                        agent_name: str,
                        action: str,
                        agent_type: AgentType = AgentType.ORCHESTRATOR,
                        level: LogLevel = LogLevel.INFO,
                        details: Optional[str] = None,
                        indent: int = 0):
        """Log an agent action with visual hierarchy."""
        indent_str = "  " * indent
        prefix = "├─" if indent > 0 else ""

        message = f"{indent_str}{prefix} {agent_type.value} [{agent_name}] {action}"
        if details:
            message += f" | {details}"

        # Create custom formatted record
        record = logging.LogRecord(
            name=self.logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None
        )
        record.custom_format = f"{datetime.now().strftime('%H:%M:%S')} | {level.value} {message}"

        self.logger.handle(record)

    def log_tool_call(self,
                     agent_name: str,
                     tool_name: str,
                     params: Optional[Dict[str, Any]] = None,
                     result_summary: Optional[str] = None,
                     indent: int = 1):
        """Log a tool call with parameters summary."""
        # Format parameters concisely
        param_str = ""
        if params:
            # Show only key parameters, not full JSON dumps
            key_params = []
            for key, value in params.items():
                if isinstance(value, str) and len(value) > 50:
                    key_params.append(f"{key}: '{value[:47]}...'")
                else:
                    key_params.append(f"{key}: {value}")
            param_str = f"({', '.join(key_params)})"

        action = f"→ {tool_name}{param_str}"
        if result_summary:
            action += f" ✓ {result_summary}"

        self.log_agent_action(
            agent_name=agent_name,
            action=action,
            agent_type=AgentType.TOOL,
            level=LogLevel.INFO,
            indent=indent
        )

    def log_subagent_lifecycle(self,
                              subagent_name: str,
                              action: str,
                              details: Optional[str] = None):
        """Log subagent creation, execution, completion."""
        level = LogLevel.SUCCESS if action in ["Created", "Completed"] else LogLevel.INFO
        self.log_agent_action(
            agent_name=subagent_name,
            action=action,
            agent_type=AgentType.SUBAGENT,
            level=level,
            details=details,
            indent=1
        )

    def log_execution_summary(self,
                            agent_name: str,
                            iterations: int,
                            tokens: int,
                            success: bool,
                            termination_reason: str):
        """Log a concise execution summary."""
        status = "SUCCESS" if success else "INCOMPLETE"
        emoji = "✅" if success else "❌"

        status_prefix = "[SUCCESS]" if success else "[INCOMPLETE]"
        summary = f"{status_prefix} {status} | {iterations} iterations | {tokens:,} tokens | {termination_reason}"

        self.log_agent_action(
            agent_name=agent_name,
            action=summary,
            agent_type=AgentType.SUBAGENT,
            level=LogLevel.SUCCESS if success else LogLevel.WARNING,
            indent=1
        )

    def log_cycle(self, cycle_number: int, action: str = "Starting"):
        """Log cycle information for multi-agent sessions."""
        border = "-" * 40
        self.logger.info(f"\n{border}")
        self.logger.info(f"CYCLE {cycle_number} | {action}")
        self.logger.info(f"{border}")

    def log_session_end(self, reason: str = "Completed"):
        """Log the end of a session."""
        border = "=" * 60
        self.logger.info(f"\n{border}")
        self.logger.info(f"SESSION ENDED: {reason}")
        self.logger.info(f"Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{border}")

    def log_error(self, agent_name: str, error: str, context: Optional[str] = None):
        """Log errors with context."""
        details = f"Error: {error}"
        if context:
            details += f" | Context: {context}"

        self.log_agent_action(
            agent_name=agent_name,
            action=details,
            level=LogLevel.ERROR
        )

    def log_llm_response(self,
                        agent_name: str,
                        content: Optional[str] = None,
                        reasoning: Optional[str] = None,
                        model: str = "unknown",
                        tokens: Optional[int] = None,
                        indent: int = 0):
        """Log LLM response content and reasoning."""
        indent_str = "  " * indent
        prefix = "├─" if indent > 0 else ""

        # Log model and token info
        model_info = f"[LLM] {model}"
        if tokens:
            model_info += f" | {tokens:,} tokens"

        record = logging.LogRecord(
            name=self.logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None
        )
        record.custom_format = f"{datetime.now().strftime('%H:%M:%S')} | {LogLevel.INFO.value} {indent_str}{prefix} {model_info}"
        self.logger.handle(record)

        # Log reasoning if available
        if reasoning:
            self.log_text_block(
                title="[REASONING]",
                content=reasoning,
                indent=indent + 1
            )

        # Log response content if available
        if content:
            self.log_text_block(
                title="[RESPONSE]",
                content=content,
                indent=indent + 1
            )

    def log_text_block(self,
                      title: str,
                      content: str,
                      indent: int = 1,
                      max_lines: int = 20):
        """Log a block of text with proper formatting and truncation."""
        indent_str = "  " * indent
        prefix = "├─" if indent > 0 else ""

        # Split content into lines and handle truncation
        lines = content.split('\n')
        if len(lines) > max_lines:
            displayed_lines = lines[:max_lines-1] + [f"... ({len(lines) - max_lines + 1} more lines truncated)"]
        else:
            displayed_lines = lines

        # Log title
        record = logging.LogRecord(
            name=self.logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None
        )
        record.custom_format = f"{datetime.now().strftime('%H:%M:%S')} | {LogLevel.INFO.value} {indent_str}{prefix} {title}"
        self.logger.handle(record)

        # Log content lines with proper indentation
        content_indent = "  " * (indent + 1)
        for line in displayed_lines:
            record = logging.LogRecord(
                name=self.logger.name,
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="",
                args=(),
                exc_info=None
            )
            record.custom_format = f"         | {content_indent}│ {line}"
            self.logger.handle(record)

    def log_raw_debug(self, message: str, level: int = logging.DEBUG):
        """Log raw debug information (API responses, etc.) at debug level."""
        if logging.root.level <= level:
            self.logger.log(level, f"[DEBUG] {message}")


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