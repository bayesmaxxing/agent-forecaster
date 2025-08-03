from typing import Any, List, Dict, Optional
import httpx 
import requests
from mcp.server.fastmcp import FastMCP
import os
import dotenv
from fastapi import FastAPI


dotenv.load_dotenv()

app = FastAPI()
mcp = FastMCP("forecasting")

# Environment variables
API_URL = os.getenv("API_URL")
BOT_USERNAME = os.getenv("BOT_USERNAME")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
# Helper functions 
async def post_request(url_postfix: str, data: Any) -> Any:
    """Make a POST request to the forecaster API"""
    url = f"{API_URL}/{url_postfix}"
    headers = {
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        return response.json()

async def get_request(url_postfix: str) -> Any:
    """Make a GET request to the forecaster API"""
    url = f"{API_URL}/{url_postfix}"
    headers = {
        "Content-Type": "application/json",
    }   

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        return response.json()

async def login() -> Any:
    """Login to the forecaster API"""
    data = {
        "password": BOT_PASSWORD,
        "username": BOT_USERNAME
    }
    response = await post_request(url_postfix="/users/login", data=data)
    return response["token"]

async def authenticated_post_request(url_postfix: str, data: Any) -> Any:
    """Make a POST request to the forecaster API with authentication"""
    token = await login()
    url = f"{API_URL}/{url_postfix}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"  
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        return response.json()

@mcp.tool(name="get_forecasts")
async def get_forecasts() -> List[Dict[str, Any]]:
    """Get a list of forecasts that have not been forecasted or where the last forecast was more than 14 days ago."""
    
    
    response = await get_request(url_postfix="forecasts/stale-and-new/18")
    if not response:
        return []
        
    return response

@mcp.tool(name="get_forecast_data")
async def get_forecast_data(id: int) -> Dict[str, Any]:
    """Get the data for a given forecast. This includes the question, the category, and the resolution criteri
    @param id: The id of the forecast to get data for
    @return: A dictionary containing the forecast data
    """
    response = await get_request(url_postfix=f"forecasts/{id}")
    if not response:
        return {"success": False, "error": "Failed to retrieve forecast data"}
        
    return {"success": True, "data": response}

@mcp.tool(name="get_forecast_points")
async def get_forecast_points(forecast_id: int) -> List[Dict[str, Any]]:
    """Get all the forecast points for a given forecast.
    @param forecast_id: The id of the forecast to get points for
    """
    response = await post_request(url_postfix=f"forecast-points/user", data={"forecast_id": forecast_id, "user_id": 18})
    if not response:
        return []
    
    return response

@mcp.tool(name="update_forecast")
async def update_forecast(forecast_id: int, point_forecast: float, reason: str) -> Dict[str, Any]:
    """Update an existing forecast with the given details
    @param forecast_id: The id of the forecast to update
    @param point_forecast: The forecast point to update
    @param reason: The reason for the forecast point
    @return: A dictionary containing the updated forecast data
    """
    if point_forecast < 0 or point_forecast > 1:
        return {"success": False, "error": "Forecast point must be between 0 and 1"}
    
    payload = {
        "forecast_id": forecast_id,
        "point_forecast": point_forecast,
        "reason": reason,
        "user_id": 0
    }
    
    response = await authenticated_post_request(url_postfix=f"/api/forecast-points", data=payload)
    if not response:
        return {"success": False, "error": "Failed to update forecast"}
        
    return {"success": True, "data": response}

@mcp.tool(name="query_perplexity")
async def query_perplexity(query_text):
    """Sends a query to the configured Perplexity model and returns the response text.
    @param query_text: The query to send to the Perplexity model
    @return: A string containing the response text
    """
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


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run()
