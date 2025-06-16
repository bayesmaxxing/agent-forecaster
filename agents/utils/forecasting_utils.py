import httpx
from typing import Any
import os
import dotenv

dotenv.load_dotenv()

API_URL = os.getenv("API_URL")
BOT_USERNAME = os.getenv("BOT_USERNAME")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")
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
    
async def put_request(url_postfix: str, data: Any) -> Any:
    """Make a PUT request to the forecaster API"""
    token = await login()
    url = f"{API_URL}/{url_postfix}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(url, json=data, headers=headers)
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