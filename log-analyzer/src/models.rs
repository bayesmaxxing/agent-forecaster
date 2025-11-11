use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct LogEntry {
    pub timestamp: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_id: Option<String>,
    #[serde(default = "default_event_type")]
    pub event_type: String,
    #[serde(default = "default_level")]
    pub level: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub agent_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub agent_type: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<serde_json::Value>,
}

fn default_event_type() -> String {
    "unknown".to_string()
}

fn default_level() -> String {
    "info".to_string()
}

#[derive(Debug, Clone)]
pub struct ToolCallData {
    pub tool_name: String,
    pub params: HashMap<String, serde_json::Value>,
    pub result_summary: Option<String>,
    pub indent: Option<u32>,
}

#[derive(Debug, Clone)]
pub struct ToolResultData {
    pub tool_name: String,
    pub result_content: String,
    pub is_error: bool,
    pub tool_call_id: Option<String>,
    pub indent: Option<u32>,
}

#[derive(Debug, Clone)]
pub struct LlmResponseData {
    pub model: String,
    pub content: Option<String>,
    pub reasoning: Option<String>,
    pub tokens: Option<TokenUsage>,
    pub indent: Option<u32>,
}

#[derive(Debug, Clone)]
pub struct TokenUsage {
    pub total: Option<u32>,
    pub prompt: Option<u32>,
    pub completion: Option<u32>,
}

#[derive(Debug, Clone)]
pub struct ExecutionSummaryData {
    pub iterations: u32,
    pub tokens: u32,
    pub success: bool,
    pub termination_reason: String,
}

#[derive(Debug, Clone)]
pub struct AgentActionData {
    pub action: String,
    pub details: Option<String>,
    pub indent: Option<u32>,
}

impl LogEntry {
    pub fn parse_tool_call(&self) -> Option<ToolCallData> {
        if self.event_type != "tool_call" {
            return None;
        }

        let data = self.data.as_ref()?;
        let tool_name = data.get("tool_name")?.as_str()?.to_string();

        let params = if let Some(p) = data.get("params") {
            if let Some(obj) = p.as_object() {
                obj.iter()
                    .map(|(k, v)| (k.clone(), v.clone()))
                    .collect()
            } else {
                HashMap::new()
            }
        } else {
            HashMap::new()
        };

        Some(ToolCallData {
            tool_name,
            params,
            result_summary: data.get("result_summary").and_then(|v| v.as_str()).map(String::from),
            indent: data.get("indent").and_then(|v| v.as_u64()).map(|v| v as u32),
        })
    }

    pub fn parse_tool_result(&self) -> Option<ToolResultData> {
        if self.event_type != "tool_result" {
            return None;
        }

        let data = self.data.as_ref()?;
        let tool_name = data.get("tool_name")?.as_str()?.to_string();
        let result_content = data.get("result_content")?.as_str()?.to_string();
        let is_error = data.get("is_error").and_then(|v| v.as_bool()).unwrap_or(false);

        Some(ToolResultData {
            tool_name,
            result_content,
            is_error,
            tool_call_id: data.get("tool_call_id").and_then(|v| v.as_str()).map(String::from),
            indent: data.get("indent").and_then(|v| v.as_u64()).map(|v| v as u32),
        })
    }

    pub fn parse_llm_response(&self) -> Option<LlmResponseData> {
        if self.event_type != "llm_response" {
            return None;
        }

        let data = self.data.as_ref()?;
        let model = data.get("model")?.as_str()?.to_string();

        let tokens = data.get("tokens").and_then(|t| {
            Some(TokenUsage {
                total: t.get("total").and_then(|v| v.as_u64()).map(|v| v as u32),
                prompt: t.get("prompt").and_then(|v| v.as_u64()).map(|v| v as u32),
                completion: t.get("completion").and_then(|v| v.as_u64()).map(|v| v as u32),
            })
        });

        Some(LlmResponseData {
            model,
            content: data.get("content").and_then(|v| v.as_str()).map(String::from),
            reasoning: data.get("reasoning").and_then(|v| v.as_str()).map(String::from),
            tokens,
            indent: data.get("indent").and_then(|v| v.as_u64()).map(|v| v as u32),
        })
    }

    pub fn parse_execution_summary(&self) -> Option<ExecutionSummaryData> {
        if self.event_type != "execution_summary" {
            return None;
        }

        let data = self.data.as_ref()?;

        Some(ExecutionSummaryData {
            iterations: data.get("iterations")?.as_u64()? as u32,
            tokens: data.get("tokens")?.as_u64()? as u32,
            success: data.get("success")?.as_bool()?,
            termination_reason: data.get("termination_reason")?.as_str()?.to_string(),
        })
    }

    pub fn parse_agent_action(&self) -> Option<AgentActionData> {
        if self.event_type != "agent_action" {
            return None;
        }

        let data = self.data.as_ref()?;
        let action = data.get("action")?.as_str()?.to_string();

        Some(AgentActionData {
            action,
            details: data.get("details").and_then(|v| v.as_str()).map(String::from),
            indent: data.get("indent").and_then(|v| v.as_u64()).map(|v| v as u32),
        })
    }
}
