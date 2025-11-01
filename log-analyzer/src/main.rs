mod models;
mod ui;

use anyhow::{Context, Result};
use clap::Parser;
use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyEventKind},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use models::*;
use ratatui::{
    backend::{Backend, CrosstermBackend},
    Terminal,
};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, BufRead, BufReader};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "log-analyzer")]
#[command(about = "Interactive TUI for analyzing JSONL logs from forecasting agents", long_about = None)]
struct Cli {
    /// Path to the JSONL log file
    file: PathBuf,
}

#[derive(Clone)]
pub struct AppState {
    pub entries: Vec<LogEntry>,
    pub selected_index: usize,
    pub scroll_offset: usize,
    pub details_scroll_offset: usize,  // New: scroll position for details panel
    pub tool_stats: ToolStats,
    pub token_stats: TokenStats,
    pub view_mode: ViewMode,
    pub filter_event_type: Option<String>,
    pub count_prefix: String,
}

#[derive(Clone, PartialEq)]
pub enum ViewMode {
    Timeline,
    Details,
}

#[derive(Clone)]
pub struct ToolStats {
    pub calls: HashMap<String, u32>,
    pub success: HashMap<String, u32>,
    pub errors: HashMap<String, u32>,
}

#[derive(Clone)]
pub struct TokenStats {
    pub total_tokens: u64,
    pub total_calls: u32,
    pub by_agent: HashMap<String, u64>,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    let entries = load_log_file(&cli.file)?;

    if entries.is_empty() {
        println!("No log entries found in file");
        return Ok(());
    }

    let tool_stats = calculate_tool_stats(&entries);
    let token_stats = calculate_token_stats(&entries);

    let mut app_state = AppState {
        entries,
        selected_index: 0,
        scroll_offset: 0,
        details_scroll_offset: 0,
        tool_stats,
        token_stats,
        view_mode: ViewMode::Timeline,
        filter_event_type: None,
        count_prefix: String::new(),
    };

    // Setup terminal
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let res = run_app(&mut terminal, &mut app_state);

    // Restore terminal
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    if let Err(err) = res {
        println!("Error: {:?}", err);
    }

    Ok(())
}

fn run_app<B: Backend>(terminal: &mut Terminal<B>, app_state: &mut AppState) -> Result<()> {
    loop {
        terminal.draw(|f| ui::draw_ui(f, app_state))?;

        if let Event::Key(key) = event::read()? {
            if key.kind == KeyEventKind::Press {
                match key.code {
                    KeyCode::Char('q') => return Ok(()),
                    KeyCode::Char(c) if c.is_ascii_digit() => {
                        // Build up count prefix
                        app_state.count_prefix.push(c);
                    }
                    KeyCode::Char('j') | KeyCode::Down => {
                        let count = app_state.count_prefix.parse::<usize>().unwrap_or(1);
                        app_state.count_prefix.clear();

                        for _ in 0..count {
                            if app_state.selected_index < app_state.entries.len().saturating_sub(1) {
                                app_state.selected_index += 1;
                            }
                        }
                        // Reset details scroll when changing selection
                        app_state.details_scroll_offset = 0;
                        // Auto-scroll
                        let visible_height = 20;
                        if app_state.selected_index >= app_state.scroll_offset + visible_height {
                            app_state.scroll_offset = app_state.selected_index.saturating_sub(visible_height - 1);
                        }
                    }
                    KeyCode::Char('k') | KeyCode::Up => {
                        let count = app_state.count_prefix.parse::<usize>().unwrap_or(1);
                        app_state.count_prefix.clear();

                        for _ in 0..count {
                            if app_state.selected_index > 0 {
                                app_state.selected_index -= 1;
                            }
                        }
                        // Reset details scroll when changing selection
                        app_state.details_scroll_offset = 0;
                        // Auto-scroll
                        if app_state.selected_index < app_state.scroll_offset {
                            app_state.scroll_offset = app_state.selected_index;
                        }
                    }
                    KeyCode::Char('h') | KeyCode::Left => {
                        // Scroll details panel up
                        app_state.count_prefix.clear();
                        if app_state.details_scroll_offset > 0 {
                            app_state.details_scroll_offset = app_state.details_scroll_offset.saturating_sub(1);
                        }
                    }
                    KeyCode::Char('l') | KeyCode::Right => {
                        // Scroll details panel down
                        app_state.count_prefix.clear();
                        app_state.details_scroll_offset += 1;
                    }
                    KeyCode::Char('d') => {
                        app_state.count_prefix.clear();
                        app_state.view_mode = match app_state.view_mode {
                            ViewMode::Timeline => ViewMode::Details,
                            ViewMode::Details => ViewMode::Timeline,
                        };
                    }
                    KeyCode::Char('g') => {
                        app_state.count_prefix.clear();
                        app_state.selected_index = 0;
                        app_state.scroll_offset = 0;
                    }
                    KeyCode::Char('G') => {
                        app_state.count_prefix.clear();
                        app_state.selected_index = app_state.entries.len().saturating_sub(1);
                        app_state.scroll_offset = app_state.entries.len().saturating_sub(20).max(0);
                    }
                    KeyCode::Char('f') => {
                        app_state.count_prefix.clear();
                        // Toggle filter (cycle through: all -> llm_response -> tool_call -> all)
                        app_state.filter_event_type = match &app_state.filter_event_type {
                            None => Some("llm_response".to_string()),
                            Some(t) if t == "llm_response" => Some("tool_call".to_string()),
                            Some(t) if t == "tool_call" => Some("tool_result".to_string()),
                            _ => None,
                        };
                        app_state.selected_index = 0;
                        app_state.scroll_offset = 0;
                    }
                    KeyCode::Esc => {
                        // Clear count prefix on escape
                        app_state.count_prefix.clear();
                    }
                    _ => {
                        // Clear count prefix on any other key
                        app_state.count_prefix.clear();
                    }
                }
            }
        }
    }
}

fn load_log_file(path: &PathBuf) -> Result<Vec<LogEntry>> {
    let file = File::open(path).context("Failed to open log file")?;
    let reader = BufReader::new(file);
    let mut entries = Vec::new();

    for (idx, line) in reader.lines().enumerate() {
        let line = line.context(format!("Failed to read line {}", idx + 1))?;
        if line.trim().is_empty() {
            continue;
        }

        match serde_json::from_str::<LogEntry>(&line) {
            Ok(entry) => entries.push(entry),
            Err(e) => eprintln!("Warning: Failed to parse line {}: {}", idx + 1, e),
        }
    }

    Ok(entries)
}

fn calculate_tool_stats(entries: &[LogEntry]) -> ToolStats {
    let mut calls = HashMap::new();
    let mut success = HashMap::new();
    let mut errors = HashMap::new();

    for entry in entries {
        if let Some(tool_call) = entry.parse_tool_call() {
            *calls.entry(tool_call.tool_name.clone()).or_insert(0) += 1;
        }

        if let Some(tool_result) = entry.parse_tool_result() {
            if tool_result.is_error {
                *errors.entry(tool_result.tool_name.clone()).or_insert(0) += 1;
            } else {
                *success.entry(tool_result.tool_name.clone()).or_insert(0) += 1;
            }
        }
    }

    ToolStats {
        calls,
        success,
        errors,
    }
}

fn calculate_token_stats(entries: &[LogEntry]) -> TokenStats {
    let mut total_tokens = 0u64;
    let mut total_calls = 0u32;
    let mut by_agent = HashMap::new();

    for entry in entries {
        if let Some(llm_data) = entry.parse_llm_response() {
            total_calls += 1;
            if let Some(tokens) = llm_data.tokens {
                if let Some(t) = tokens.total {
                    total_tokens += t as u64;
                    if let Some(agent) = &entry.agent_name {
                        *by_agent.entry(agent.clone()).or_insert(0) += t as u64;
                    }
                }
            }
        }
    }

    TokenStats {
        total_tokens,
        total_calls,
        by_agent,
    }
}
