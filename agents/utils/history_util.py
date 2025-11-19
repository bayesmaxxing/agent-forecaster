"""Message history with token tracking and prompt caching."""

from typing import Any
from openai import OpenAI
import os

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
        reasoning_details: str = "",
        usage: Any | None = None,
    ):
        """Add a message to the history and track token usage."""
        # Handle OpenAI message format
        if hasattr(content, 'content') and hasattr(content, 'tool_calls'):
            # This is an OpenAI ChatCompletion message
            message = {
                "role": role,
                "content": content.content,
            }
            # Only add reasoning_details to assistant messages when it exists
            if role == "assistant" and reasoning_details:
                message["reasoning_details"] = reasoning_details
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
            # Only add reasoning_details to assistant messages when it exists
            if role == "assistant" and reasoning_details:
                message["reasoning_details"] = reasoning_details
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
                # Only add reasoning_details to assistant messages when it exists
                if role == "assistant" and reasoning_details:
                    message["reasoning_details"] = reasoning_details
        else:
            message = {"role": role, "content": str(content)}
            # Only add reasoning_details to assistant messages when it exists
            if role == "assistant" and reasoning_details:
                message["reasoning_details"] = reasoning_details

        self.messages.append(message)

        if role == "assistant" and usage:
            # OpenAI usage format
            total_input = getattr(usage, 'prompt_tokens', 0)
            output_tokens = getattr(usage, 'completion_tokens', 0)

            current_turn_input = total_input - self.total_tokens
            self.message_tokens.append((current_turn_input, output_tokens))
            self.total_tokens += current_turn_input + output_tokens


    def compact(self, keep_recent: int = 3) -> None:
        """Compact the message history by summarizing older messages."""
        # Only compact if we are approaching the context limit (e.g. > 90% full)
        # or if explicitly requested (logic can be adjusted)
        if self.total_tokens < self.context_window_tokens * 0.9:
            return

        if len(self.messages) <= keep_recent:
            return

        # Separate messages to summarize and messages to keep
        to_summarize = self.messages[:-keep_recent]
        recent_messages = self.messages[-keep_recent:]

        # Prepare prompt for summarization
        summary_system_prompt = (
            "You are a helpful assistant that summarizes the message history of AI agents. "
            "Summarize the provided conversation history into a concise but comprehensive narrative. "
            "Include key decisions, actions taken, tool outputs, and important information gathered. "
            "The summary will be used as context for the agent to continue its task."
        )

        # Format messages for the summarizer
        summary_content = ""
        for msg in to_summarize:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, list): 
                 content = str(content)
            
            summary_content += f"{role.upper()}: {content}\n\n"
            
            if "tool_calls" in msg:
                for tc in msg["tool_calls"]:
                    func = tc.get("function", {})
                    name = func.get("name", "unknown")
                    args = func.get("arguments", "")
                    summary_content += f"TOOL_CALL ({name}): {args}\n\n"

        messages_for_summary = [
            {"role": "system", "content": summary_system_prompt},
            {"role": "user", "content": f"Here is the conversation history to summarize:\n\n{summary_content}"}
        ]

        # Call LLM for summary using the existing client
        # We try to use a fast model for summarization
        try:
             response = self.client.chat.completions.create(
                model="anthropic/claude-haiku-4.5",
                messages=messages_for_summary,
                max_tokens=10000
            )
             summary_text = response.choices[0].message.content
        except Exception as e:
            # Fallback to standard truncation if summarization fails
            print(f"Compaction failed: {e}. Falling back to truncation.")
            self.truncate()
            return

        # We insert this as a user message with context info
        summary_message = {
            "role": "user", 
            "content": f"[Previous Context Summary]: {summary_text}",
        }

        self.messages = [summary_message] + recent_messages
        
        # Recalculate token usage estimate
        try:
            sys_tokens = len(self.system) / 4
        except:
            sys_tokens = 0
            
        summary_tokens = len(summary_text) / 4
        
        recent_tokens = 0
        for msg in recent_messages:
            content = str(msg.get("content", ""))
            recent_tokens += len(content) / 4
            
        self.total_tokens = int(sys_tokens + summary_tokens + recent_tokens)
        
        # Reset message_tokens as the correspondence is lost
        self.message_tokens = []
        

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
            # Only include reasoning_details for assistant messages when it exists
            if m["role"] == "assistant" and "reasoning_details" in m and m["reasoning_details"]:
                message["reasoning_details"] = m["reasoning_details"]
            # Include tool_calls if present
            if "tool_calls" in m:
                message["tool_calls"] = m["tool_calls"]
            # Include tool_call_id if present (for tool messages)
            if "tool_call_id" in m:
                message["tool_call_id"] = m["tool_call_id"]
            formatted_messages.append(message)
        return formatted_messages
