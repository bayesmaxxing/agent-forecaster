# Superforecaster testbed 

The Superforecaster testbed is an experimental repository for me to try creating AI Agents in an environment I'm familiar with, forecasting. The original repository is based on Anthropic Quickstarts which is a collection of projects designed to help developers quickly get started with building  applications using the Anthropic API.

## Current agents 

So far, I've created one single-agent system that iteratively uses tools like a forecasting MCP that allows the agent to communicate with my personal forecasting website. The agent also has access to Perplexity to fetch information.

Going forward, I'll try to build a multi-agent system that consists of one Coordinator that spawns sub-agents with specific tasks and tools related to the task. After I've built this, I want to evaluate these approaches to see which agent architecture works best.

## Other improvements

Due to being based on an Anthropic repo, the code is custom-built for the Anthropic API. I would like to make the code more generic and flexible, such that it is possible to run the same workflow/agent setup for OpenAI, Gemini, and Grok models. This is also tbd.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
