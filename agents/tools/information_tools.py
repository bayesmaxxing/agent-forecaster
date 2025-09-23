"""Tools for gathering information."""

import asyncio
import glob
import os
from pathlib import Path
import requests
import dotenv
from .base import Tool
from openai import OpenAI

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
    
class RequestFeedbackTool(Tool):
    def __init__(self):
        super().__init__(
            name="request_feedback",
            description="Use the tool to request feedback on a forecast.",
            input_schema={
                "type": "object",
                "properties": {
                    "feedback_text": {
                        "type": "string",
                        "description": "The reasoning that you want to request feedback on.",
                    },
                    "forecast_info": {
                        "type": "string",
                        "description": "Detailed information about the forecast that you want to request feedback on. Such as the question and the resolution criteria.",
                    }
                },
            }
        )
    
    async def execute(self, feedback_text: str, forecast_info: str):
        """Execute the information tools."""
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", "")
        )

        response = client.chat.completions.create(
            model="openai/gpt-5",
            messages=[
                {"role": "system", "content": """
                You are superforecaster that provides feedback on forecasts given to you by the user.
                You will be given the reasoning for making a forecast. Your task is to investigate the reasoning for flaws
                and provide feedback and critiques on the reasoning. The feedback should be concise and to the point.
                You are allowed to suggest ideas for improvement. If the user provides you with detailed information about the forecast, make sure that 
                the user has understood and followed the details of the forecast.
                The user has no ability to edit the forecast question or resolution criteria. Don't give feedback on those, instead make sure that the user has 
                understood and followed the details of the forecast.
                """},
                {"role": "user", "content": feedback_text},
                {"role": "user", "content": f"Here is some detailed information about the forecast: {forecast_info}"}
            ],
            max_tokens=2000,
            verbosity="low",
        )
        message = response.choices[0].message
        # Handle reasoning models that put content in reasoning field
        if message.content and message.content.strip():
            return message.content
        elif hasattr(message, 'reasoning') and message.reasoning:
            return message.reasoning
        else:
            return str(message)
