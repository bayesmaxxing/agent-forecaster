import httpx
from typing import Any
import os
import dotenv
from pathlib import Path

# Try to load .env file from multiple possible locations
env_paths = [
    Path(__file__).parent.parent.parent / ".env",  # Project root
    Path(__file__).parent.parent / "tools" / ".env",  # tools folder
    Path(__file__).parent / ".env",  # utils folder
]

for env_path in env_paths:
    if env_path.exists():
        dotenv.load_dotenv(env_path)
        break
else:
    # If no .env file found, try loading from current directory
    dotenv.load_dotenv()

API_URL = os.getenv("API_URL")

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

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
    
async def put_request(url_postfix: str, data: Any, user_name: str, user_password: str) -> Any:
    """Make a PUT request to the forecaster API"""
    token = await login(user_name=user_name, user_password=user_password)
    url = f"{API_URL}/{url_postfix}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(url, json=data, headers=headers)
        return response.json()


async def login(user_name: str, user_password: str) -> Any:
    """Login to the forecaster API"""
    data = {
        "username": user_name,
        "password": user_password,
    }
    response = await post_request(url_postfix="users/login", data=data)
    return response["token"]

async def authenticated_post_request(url_postfix: str, data: Any, user_name: str, user_password: str) -> Any:
    """Make a POST request to the forecaster API with authentication"""
    token = await login(user_name=user_name, user_password=user_password)
    url = f"{API_URL}/{url_postfix}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"  
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        return response.json()
