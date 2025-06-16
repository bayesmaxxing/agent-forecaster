"""Tools for forecasting. Converted from the forecasting_mcp.py file."""
from agents.utils import post_request, get_request, authenticated_post_request
from .base import Tool

class GetForecastsTool(Tool):
    def __init__(self):
        super().__init__(
            name="get_forecasts",
            description="Use the tool to get a list of forecasts that are available for you to forecast.",
            input_schema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "The category of forecasts to get."
                    },
                    "list_type": {
                        "type": "string",
                        "description": "The type of list to get. Can be 'open', 'closed', or 'all'."
                    }
                },
            }
        )
    
    async def execute(self, category: str = None, list_type: str = "open"):
        """Execute the forecasting tools."""
        payload = {"list_type": list_type}
        
        if category:
            payload["category"] = category
        
        response = await post_request(url_postfix="forecasts", data=payload)
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
    def __init__(self):
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
    
    async def execute(self, forecast_id: int):
        """Execute the forecasting tools."""
        response = await post_request(url_postfix=f"forecast-points/user", data={"forecast_id": forecast_id, "user_id": 18})
        if not response:
            return {"success": False, "error": "Failed to retrieve forecast points"}
        
        return {"success": True, "data": response}
    
class UpdateForecastTool(Tool):
    def __init__(self):
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

        response = await authenticated_post_request(url_postfix=f"forecast-points", data=payload)
        if not response:
            return {"success": False, "error": "Failed to update forecast"}
        
        return {"success": True, "data": response}
        