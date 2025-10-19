"""Tools for forecasting. Converted from the forecasting_mcp.py file."""
from ..utils import post_request, get_request, authenticated_post_request
from .base import Tool
import dotenv
import os
dotenv.load_dotenv()

class GetForecastsTool(Tool):
    def __init__(self, model: str):
        super().__init__(
            name="get_forecasts",
            description="Use the tool to get a list of forecasts that are available for you to forecast.",
            input_schema={
                "type": "object",
                "properties": {
                },
            }
        )
        self.model = model
        if self.model.lower() == "opus":
            self.user_id = 18
        elif self.model.lower() == "gpt-5":
            self.user_id = 19
        elif self.model.lower() == "grok":
            self.user_id = 20
        elif self.model.lower() == "gemini":
            self.user_id = 21
        elif self.model.lower() == "multi":
            self.user_id = 22
        else: 
            raise ValueError("Invalid model")

    async def execute(self):
        """Execute the forecasting tools."""
        
        response = await get_request(url_postfix=f"forecasts/stale-and-new/{self.user_id}")
        return response
    
class GetForecastDataTool(Tool):
    def __init__(self):
        super().__init__(
            name="get_forecast_data",
            description="Use the tool to get the data for a forecast.",
            input_schema={
                "type": "object",
                "properties": {
                    "forecast_id": {
                        "type": "integer",
                        "description": "The ID of the forecast to get data for."
                    }
                },
            }
        )
    
    async def execute(self, forecast_id: int):
        """Execute the forecasting tools."""
        response = await get_request(url_postfix=f"forecasts/{forecast_id}")
        if not response:
            return {"success": False, "error": "Failed to retrieve forecast data"}
        
        return {"success": True, "data": response}
    
class GetForecastPointsTool(Tool):
    def __init__(self, model: str):
        super().__init__(
            name="get_forecast_points",
            description="Use the tool to get the forecast points for a forecast.",
            input_schema={
                "type": "object",
                "properties": {
                    "forecast_id": {
                        "type": "integer",
                        "description": "The ID of the forecast to get points for."
                    }
                },
            }
        )
        self.model = model
        if self.model.lower() == "opus":
            self.user_id = 18
        elif self.model.lower() == "gpt-5":
            self.user_id = 19
        elif self.model.lower() == "grok":
            self.user_id = 20
        elif self.model.lower() == "gemini":
            self.user_id = 21
        elif self.model.lower() == "multi":
            self.user_id = 22
        else: 
            raise ValueError("Invalid model")
            
    async def execute(self, forecast_id: int):
        """Execute the forecasting tools."""
        try:
            response = await post_request(url_postfix=f"forecast-points/user", data={"forecast_id": forecast_id, "user_id": self.user_id})
            return {"success": True, "data": response}
        except Exception as e:
            return {"success": False, "error": f"Failed to retrieve forecast points: {str(e)}"}

class GetPointsCreatedToday(Tool):
    def __init__(self, model: str):
        super().__init__(
            name="get_points_created_today",
            description="Use the tool to get the points created today.",
            input_schema={
                "type": "object",
                "properties": {},
            }
        )
        self.model = model
        if self.model.lower() == "opus":
            self.user_id = 18
        elif self.model.lower() == "gpt-5":
            self.user_id = 19
        elif self.model.lower() == "grok":
            self.user_id = 20
        elif self.model.lower() == "gemini":
            self.user_id = 21
        elif self.model.lower() == "multi":
            self.user_id = 22
        else:
            raise ValueError("Invalid model")

    async def execute(self):
        """Execute the points created today tool."""
        response = await get_request(url_postfix=f"forecast-points/today/{self.user_id}")
        return response

class UpdateForecastTool(Tool):
    def __init__(self, model: str):
        super().__init__(
            name="update_forecast",
            description="Use the tool to update a forecast.",
            input_schema={
                "type": "object",
                "properties": {
                    "forecast_id": {
                        "type": "integer",
                        "description": "The ID of the forecast to update."
                    },
                    "point_forecast": {
                        "type": "number",
                        "description": "The new point forecast."
                    },
                    "reason": {
                        "type": "string",
                        "description": "The reason for the update."
                    }
                },
            }
        )
        self.model = model
        if self.model.lower() == "opus":
            self.user_name = os.getenv("ANTHROPIC_BOT_USERNAME")
            self.user_password = os.getenv("ANTHROPIC_BOT_PASSWORD")
        elif self.model.lower() == "gpt-5":
            self.user_name = os.getenv("OPENAI_BOT_USERNAME")
            self.user_password = os.getenv("OPENAI_BOT_PASSWORD")
        elif self.model.lower() == "grok":
            self.user_name = os.getenv("GROK_BOT_USERNAME")
            self.user_password = os.getenv("GROK_BOT_PASSWORD")
        elif self.model.lower() == "gemini":
            self.user_name = os.getenv("GEMINI_BOT_USERNAME")
            self.user_password = os.getenv("GEMINI_BOT_PASSWORD")
        elif self.model.lower() == "multi":
            self.user_name = os.getenv("MULTI_BOT_USERNAME")
            self.user_password = os.getenv("MULTI_BOT_PASSWORD")
        else:
            raise ValueError("Invalid model")
            
    
    async def execute(self, forecast_id: int, point_forecast: float, reason: str):
        """Execute the forecasting tools."""
        if point_forecast < 0 or point_forecast > 1:
            return {"success": False, "error": "Point forecast must be between 0 and 1"}
        
        payload = {
            "forecast_id": forecast_id,
            "point_forecast": point_forecast,
            "reason": reason,
            "user_id": 0
        }
        
        response = await authenticated_post_request(url_postfix=f"api/forecast-points", data=payload, user_name=self.user_name, user_password=self.user_password)
        if not response:
            return {"success": False, "error": "Failed to update forecast"}
        
        return {"success": True, "data": response}
        