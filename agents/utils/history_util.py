"""Message history with token tracking and prompt caching."""

from typing import Any


class MessageHistory:
    """Manages chat history with token tracking and context management."""

    def __init__(
        self,
        model: str,
        system: str,
        context_window_tokens: int,
        client: Any,
        enable_caching: bool = True,
    ):
        self.model = model
        self.system = system
        self.context_window_tokens = context_window_tokens
        self.messages: list[dict[str, Any]] = []
        self.total_tokens = 0
        self.enable_caching = enable_caching
        self.message_tokens: list[tuple[int, int]] = (
            []
        )  # List of (input_tokens, output_tokens) tuples
        self.client = client

        # set initial total tokens to system prompt (rough estimate for OpenAI)
        try:
            # OpenAI doesn't have a token counting API in the same way
            # Use rough estimate: ~4 chars per token
            system_token = len(self.system) / 4
        except Exception:
            system_token = len(self.system) / 4

        self.total_tokens = system_token

    async def add_message(
        self,
        role: str,
        content: str | list[dict[str, Any]] | Any,
        usage: Any | None = None,
    ):
        """Add a message to the history and track token usage."""
        # Handle OpenAI message format
        if hasattr(content, 'content') and hasattr(content, 'tool_calls'):
            # This is an OpenAI ChatCompletion message
            message = {
                "role": role,
                "content": content.content
            }
            if content.tool_calls:
                message["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in content.tool_calls
                ]
        elif isinstance(content, list) and all(isinstance(item, dict) and 'tool_call_id' in item for item in content):
            # This is tool results - add each tool result as a separate message
            for item in content:
                message = {
                    "role": "tool",
                    "content": item.get('content', ''),
                    "tool_call_id": item.get('tool_call_id', '')
                }
                self.messages.append(message)
            return  # Don't add the list as a single message
        elif isinstance(content, str):
            message = {"role": role, "content": content}
        elif isinstance(content, list):
            # Handle legacy format or tool results
            if all(isinstance(item, dict) and 'content' in item for item in content):
                # Tool results format
                message = {
                    "role": "tool", 
                    "content": str([item['content'] for item in content])
                }
            else:
                message = {"role": role, "content": str(content)}
        else:
            message = {"role": role, "content": str(content)}

        self.messages.append(message)

        if role == "assistant" and usage:
            # OpenAI usage format
            total_input = getattr(usage, 'prompt_tokens', 0)
            output_tokens = getattr(usage, 'completion_tokens', 0)

            current_turn_input = total_input - self.total_tokens
            self.message_tokens.append((current_turn_input, output_tokens))
            self.total_tokens += current_turn_input + output_tokens

    def truncate(self) -> None:
        """Remove oldest messages when context window limit is exceeded."""
        if self.total_tokens <= self.context_window_tokens:
            return

        TRUNCATION_NOTICE_TOKENS = 25
        # Simplified truncation message for OpenAI format
        TRUNCATION_MESSAGE = {
            "role": "user",
            "content": "[Earlier history has been truncated.]"
        }

        def remove_message_pair():
            self.messages.pop(0)
            self.messages.pop(0)

            if self.message_tokens:
                input_tokens, output_tokens = self.message_tokens.pop(0)
                self.total_tokens -= input_tokens + output_tokens

        while (
            self.message_tokens
            and len(self.messages) >= 2
            and self.total_tokens > self.context_window_tokens
        ):
            remove_message_pair()

            if self.messages and self.message_tokens:
                original_input_tokens, original_output_tokens = (
                    self.message_tokens[0]
                )
                self.messages[0] = TRUNCATION_MESSAGE
                self.message_tokens[0] = (
                    TRUNCATION_NOTICE_TOKENS,
                    original_output_tokens,
                )
                self.total_tokens += (
                    TRUNCATION_NOTICE_TOKENS - original_input_tokens
                )

    def format_for_api(self) -> list[dict[str, Any]]:
        """Format messages for OpenAI API."""
        # Include all fields from messages, not just role and content
        formatted_messages = []
        for m in self.messages:
            message = {"role": m["role"], "content": m["content"]}
            # Include tool_calls if present
            if "tool_calls" in m:
                message["tool_calls"] = m["tool_calls"]
            # Include tool_call_id if present (for tool messages)
            if "tool_call_id" in m:
                message["tool_call_id"] = m["tool_call_id"]
            formatted_messages.append(message)
        return formatted_messages
