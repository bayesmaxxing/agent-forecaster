use crate::{AppState, ViewMode};
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span, Text},
    widgets::{Block, Borders, List, ListItem, Paragraph, Wrap},
    Frame,
};

pub fn draw_ui(f: &mut Frame, app_state: &AppState) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(8),  // Stats panel (expanded for session ID)
            Constraint::Min(10),    // Main content
            Constraint::Length(3),  // Help bar
        ])
        .split(f.area());

    draw_stats_panel(f, chunks[0], app_state);
    draw_main_content(f, chunks[1], app_state);
    draw_help_bar(f, chunks[2], app_state);
}

fn draw_stats_panel(f: &mut Frame, area: Rect, app_state: &AppState) {
    let chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(area);

    // Session info
    let session_id = app_state.entries.first()
        .and_then(|e| e.session_id.as_ref())
        .map(|s| s.as_str())
        .unwrap_or("unknown");

    // Token stats
    let token_text = vec![
        Line::from(vec![
            Span::styled("Session: ", Style::default().fg(Color::Cyan)),
            Span::styled(
                format!("{}", session_id),
                Style::default().fg(Color::Green),
            ),
        ]),
        Line::from(vec![
            Span::styled("Total Tokens: ", Style::default().fg(Color::Cyan)),
            Span::styled(
                format!("{}", app_state.token_stats.total_tokens),
                Style::default().fg(Color::Yellow),
            ),
        ]),
        Line::from(vec![
            Span::styled("LLM Calls: ", Style::default().fg(Color::Cyan)),
            Span::raw(format!("{}", app_state.token_stats.total_calls)),
        ]),
        Line::from(vec![
            Span::styled("Total Events: ", Style::default().fg(Color::Cyan)),
            Span::raw(format!("{}", app_state.entries.len())),
        ]),
    ];

    let token_panel = Paragraph::new(token_text)
        .block(Block::default().title("Session Stats").borders(Borders::ALL));
    f.render_widget(token_panel, chunks[0]);

    // Tool stats
    let mut tool_lines = vec![Line::from(Span::styled(
        "Tool Usage:",
        Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
    ))];

    let mut tools: Vec<_> = app_state.tool_stats.calls.iter().collect();
    tools.sort_by(|a, b| b.1.cmp(a.1));

    for (tool, count) in tools.iter().take(3) {
        let success = app_state.tool_stats.success.get(*tool).unwrap_or(&0);
        let errors = app_state.tool_stats.errors.get(*tool).unwrap_or(&0);

        tool_lines.push(Line::from(vec![
            Span::raw(format!("  {}: ", tool)),
            Span::styled(format!("{}", count), Style::default().fg(Color::White)),
            Span::raw(" ("),
            Span::styled(format!("✓{}", success), Style::default().fg(Color::Green)),
            Span::raw("/"),
            Span::styled(format!("✗{}", errors), Style::default().fg(Color::Red)),
            Span::raw(")"),
        ]));
    }

    let tool_panel = Paragraph::new(tool_lines)
        .block(Block::default().title("Top Tools").borders(Borders::ALL));
    f.render_widget(tool_panel, chunks[1]);
}

fn draw_main_content(f: &mut Frame, area: Rect, app_state: &AppState) {
    if app_state.view_mode == ViewMode::Details {
        let chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(60), Constraint::Percentage(40)])
            .split(area);
        draw_timeline(f, chunks[0], app_state);
        draw_details_panel(f, chunks[1], app_state);
    } else {
        draw_timeline(f, area, app_state);
    }
}

fn draw_timeline(f: &mut Frame, area: Rect, app_state: &AppState) {
    let entries = &app_state.entries;

    let filtered_entries: Vec<_> = if let Some(ref filter) = app_state.filter_event_type {
        entries
            .iter()
            .enumerate()
            .filter(|(_, e)| e.event_type == *filter)
            .collect()
    } else {
        entries.iter().enumerate().collect()
    };

    let items: Vec<ListItem> = filtered_entries
        .iter()
        .skip(app_state.scroll_offset)
        .take(area.height as usize - 2)
        .map(|(idx, entry)| {
            let is_selected = *idx == app_state.selected_index;

            let time = entry
                .timestamp
                .split('T')
                .nth(1)
                .and_then(|t| t.split('.').next())
                .unwrap_or(&entry.timestamp);

            let (icon, color, detail) = match entry.event_type.as_str() {
                "llm_response" => {
                    let model = entry
                        .parse_llm_response()
                        .map(|l| l.model)
                        .unwrap_or_else(|| "unknown".to_string());
                    ("🤖", Color::Blue, format!("LLM: {}", model))
                }
                "tool_call" => {
                    let tool = entry
                        .parse_tool_call()
                        .map(|t| t.tool_name)
                        .unwrap_or_else(|| "unknown".to_string());
                    ("🔧", Color::Green, format!("Tool Call: {}", tool))
                }
                "tool_result" => {
                    let result = entry.parse_tool_result();
                    let tool = result
                        .as_ref()
                        .map(|t| t.tool_name.clone())
                        .unwrap_or_else(|| "unknown".to_string());
                    let status = result
                        .as_ref()
                        .map(|r| if r.is_error { "✗" } else { "✓" })
                        .unwrap_or("?");
                    ("📦", Color::Cyan, format!("Result {}: {}", status, tool))
                }
                "agent_action" => {
                    let action = entry
                        .parse_agent_action()
                        .map(|a| a.action)
                        .unwrap_or_else(|| "unknown".to_string());
                    ("⚡", Color::Yellow, format!("Action: {}", action))
                }
                "execution_summary" => ("📊", Color::Magenta, "Execution Summary".to_string()),
                "session_start" => ("🚀", Color::Green, "Session Start".to_string()),
                "session_end" => ("🏁", Color::Red, "Session End".to_string()),
                _ => ("•", Color::Gray, entry.event_type.clone()),
            };

            let agent = entry
                .agent_name
                .as_ref()
                .map(|a| format!("[{}]", a))
                .unwrap_or_else(|| "".to_string());

            let line = Line::from(vec![
                Span::styled(time, Style::default().fg(Color::DarkGray)),
                Span::raw(" "),
                Span::styled(icon, Style::default().fg(color)),
                Span::raw(" "),
                Span::styled(detail, Style::default().fg(color)),
                Span::raw(" "),
                Span::styled(agent, Style::default().fg(Color::Cyan)),
            ]);

            let style = if is_selected {
                Style::default()
                    .bg(Color::DarkGray)
                    .add_modifier(Modifier::BOLD)
            } else {
                Style::default()
            };

            ListItem::new(line).style(style)
        })
        .collect();

    let filter_info = if let Some(ref f) = app_state.filter_event_type {
        format!(" [Filter: {}]", f)
    } else {
        "".to_string()
    };

    let title = format!(
        "Timeline ({}/{}){}",
        app_state.selected_index + 1,
        app_state.entries.len(),
        filter_info
    );

    let list = List::new(items).block(Block::default().title(title).borders(Borders::ALL));

    f.render_widget(list, area);
}

fn draw_details_panel(f: &mut Frame, area: Rect, app_state: &AppState) {
    if app_state.selected_index >= app_state.entries.len() {
        return;
    }

    let entry = &app_state.entries[app_state.selected_index];
    let mut lines = vec![
        Line::from(vec![
            Span::styled("Event: ", Style::default().fg(Color::Cyan)),
            Span::raw(&entry.event_type),
        ]),
        Line::from(vec![
            Span::styled("Time: ", Style::default().fg(Color::Cyan)),
            Span::raw(&entry.timestamp),
        ]),
    ];

    if let Some(agent) = &entry.agent_name {
        lines.push(Line::from(vec![
            Span::styled("Agent: ", Style::default().fg(Color::Cyan)),
            Span::raw(agent),
        ]));
    }

    lines.push(Line::from(""));

    match entry.event_type.as_str() {
        "llm_response" => {
            if let Some(llm) = entry.parse_llm_response() {
                lines.push(Line::from(Span::styled(
                    "Model:",
                    Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
                )));
                lines.push(Line::from(format!("  {}", llm.model)));

                if let Some(tokens) = llm.tokens {
                    lines.push(Line::from(""));
                    lines.push(Line::from(Span::styled(
                        "Tokens:",
                        Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
                    )));
                    if let Some(total) = tokens.total {
                        lines.push(Line::from(format!("  Total: {}", total)));
                    }
                    if let Some(prompt) = tokens.prompt {
                        lines.push(Line::from(format!("  Prompt: {}", prompt)));
                    }
                    if let Some(completion) = tokens.completion {
                        lines.push(Line::from(format!("  Completion: {}", completion)));
                    }
                }

                if let Some(reasoning) = &llm.reasoning {
                    lines.push(Line::from(""));
                    lines.push(Line::from(Span::styled(
                        "Reasoning:",
                        Style::default().fg(Color::Magenta).add_modifier(Modifier::BOLD),
                    )));
                    for line in reasoning.lines().take(10) {
                        lines.push(Line::from(format!("  {}", line)));
                    }
                }

                if let Some(content) = &llm.content {
                    lines.push(Line::from(""));
                    lines.push(Line::from(Span::styled(
                        "Content:",
                        Style::default().fg(Color::Blue).add_modifier(Modifier::BOLD),
                    )));
                    for line in content.lines().take(10) {
                        lines.push(Line::from(format!("  {}", line)));
                    }
                }
            }
        }
        "tool_call" => {
            if let Some(tool) = entry.parse_tool_call() {
                lines.push(Line::from(Span::styled(
                    "Tool:",
                    Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
                )));
                lines.push(Line::from(format!("  {}", tool.tool_name)));

                if !tool.params.is_empty() {
                    lines.push(Line::from(""));
                    lines.push(Line::from(Span::styled(
                        "Parameters:",
                        Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
                    )));
                    for (key, value) in tool.params.iter() {
                        let val_str = format!("{}", value);
                        lines.push(Line::from(format!("  {}: {}", key, val_str)));
                    }
                }
            }
        }
        "tool_result" => {
            if let Some(result) = entry.parse_tool_result() {
                lines.push(Line::from(vec![
                    Span::styled("Tool: ", Style::default().fg(Color::Cyan)),
                    Span::raw(result.tool_name.clone()),
                ]));

                let status = if result.is_error {
                    Span::styled("✗ Error", Style::default().fg(Color::Red))
                } else {
                    Span::styled("✓ Success", Style::default().fg(Color::Green))
                };
                lines.push(Line::from(vec![Span::styled("Status: ", Style::default().fg(Color::Cyan)), status]));

                lines.push(Line::from(""));
                lines.push(Line::from(Span::styled(
                    "Result:",
                    Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
                )));

                for line in result.result_content.lines().take(15) {
                    lines.push(Line::from(format!("  {}", line)));
                }
            }
        }
        _ => {
            if let Some(data) = &entry.data {
                lines.push(Line::from(Span::styled(
                    "Data:",
                    Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
                )));
                let data_str = serde_json::to_string_pretty(data).unwrap_or_default();
                for line in data_str.lines().take(20) {
                    lines.push(Line::from(format!("  {}", line)));
                }
            }
        }
    }

    let text = Text::from(lines);
    let paragraph = Paragraph::new(text)
        .block(Block::default().title("Details").borders(Borders::ALL))
        .wrap(Wrap { trim: true });

    f.render_widget(paragraph, area);
}

fn draw_help_bar(f: &mut Frame, area: Rect, app_state: &AppState) {
    let mut help_spans = vec![
        Span::raw(" "),
        Span::styled("q", Style::default().fg(Color::Yellow)),
        Span::raw(":Quit "),
        Span::styled("[count]j/k", Style::default().fg(Color::Yellow)),
        Span::raw(":Navigate "),
        Span::styled("d", Style::default().fg(Color::Yellow)),
        Span::raw(":Details "),
        Span::styled("f", Style::default().fg(Color::Yellow)),
        Span::raw(":Filter "),
        Span::styled("g/G", Style::default().fg(Color::Yellow)),
        Span::raw(":Top/Bottom "),
        Span::raw(format!(
            " | Mode: {}",
            if app_state.view_mode == ViewMode::Details {
                "Details"
            } else {
                "Timeline"
            }
        )),
    ];

    // Show count prefix if user is typing one
    if !app_state.count_prefix.is_empty() {
        help_spans.push(Span::raw(" | "));
        help_spans.push(Span::styled(
            format!("Count: {}", app_state.count_prefix),
            Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
        ));
    }

    let help_text = vec![Line::from(help_spans)];

    let help = Paragraph::new(help_text).block(Block::default().borders(Borders::ALL));
    f.render_widget(help, area);
}
