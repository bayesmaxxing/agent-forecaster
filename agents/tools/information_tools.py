"""Tools for gathering information."""

import asyncio
import glob
import os
from pathlib import Path
import requests
import dotenv
from .base import Tool

dotenv.load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")


class QueryPerplexityTool(Tool):
    def __init__(self):
        super().__init__(
            name="query_perplexity",
            description="Use the tool to query Perplexity for up-to-date information and news articles.",
            input_schema={
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "The query text to search for."
                    }
                },
            }
        )
    
    async def execute(self, query_text: str):
        """Execute the information tools."""
        url = "https://api.perplexity.ai/chat/completions"
        payload = {
            "model": "sonar",
            "messages": [
                {"role": "system", "content": """You are a helpful assistant that provides information and the latest news on a given topic.
                The information you provide will be used for forecasting purposes, so it should be up to date, relevant and accurate."""},
                {"role": "user", "content": query_text}
            ],
            "max_tokens": 2000
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}"
        }
        
        with requests.post(url, json=payload, headers=headers) as response:
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    