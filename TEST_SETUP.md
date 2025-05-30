# Agent Test Setup

This guide helps you test the forecasting agent in a terminal environment.

## Prerequisites

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Configure environment variables**:
   Edit `agents/tools/.env` and add your API keys:
   ```bash
   # Edit the .env file
   nano agents/tools/.env
   ```
   
   At minimum, set your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your-actual-api-key-here
   ```

## Running the Test

```bash
uv run python test_agent.py
```

## Example Interactions

Once the agent is running, you can try these example questions:

### Basic Forecasting Queries
- "What forecasts are currently available?"
- "Show me open forecasts in the technology category"
- "Get me details about forecast ID 123"

### Information Gathering
- "What's the latest news about AI development?"
- "Search for recent information about climate change"
- "What are the current trends in cryptocurrency?"

### Forecasting Updates (requires API authentication)
- "Update forecast 456 with a probability of 0.75 because of recent developments"
- "I want to make a new forecast about the upcoming election"

## Available Tools

The agent has access to these forecasting tools:

1. **get_forecasts** - Get lists of forecasts by category and status
2. **get_forecast_data** - Get detailed information about specific forecasts
3. **get_forecast_points** - Get historical prediction points for a forecast
4. **update_forecast** - Submit new predictions with reasoning
5. **query_perplexity** - Search for current information on any topic

## Troubleshooting

- **Import errors**: Make sure you've run `uv sync` to install dependencies
- **API errors**: Verify your ANTHROPIC_API_KEY is set correctly
- **MCP connection issues**: The forecasting MCP will run automatically when the agent starts
- **Forecasting API errors**: These are expected if you don't have the forecasting service running

## Stopping the Test

Type `quit`, `exit`, or `q` to stop the agent, or use Ctrl+C.