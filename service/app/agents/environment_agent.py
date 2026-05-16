from typing import Any, Dict
import logging
from ..models.task import Task, TaskStatus
from ..core.climate_api import ClimateAPI, ClimateAPIError
from ..core.config import settings
from ..core.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class EnvironmentAgent:
    def __init__(self):
        if not settings.openweather_api_key:
            raise RuntimeError(
                "openweather_api_key is required in settings. "
                "Set OPENWEATHER_API_KEY environment variable."
            )
        self.climate_api = ClimateAPI(api_key=settings.openweather_api_key)
        self.gemini_client = GeminiClient()
        self.name = "EnvironmentAgent"

    def log(self, message: str):
        logger.info(f"[{self.name}] {message}")

    async def execute(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        task.status = TaskStatus.PENDING
        task.progress = 10

        location_info = self._extract_location(context)

        self.log(f"Querying climate data for {location_info['name']}...")
        climate_data = await self.climate_api.get_climate_data(
            latitude=location_info["latitude"],
            longitude=location_info["longitude"],
            city_name=location_info["name"]
        )

        self.log("Generating building codes via LLM...")
        building_codes = await self._get_building_codes_via_llm(
            country=location_info["country"],
            climate_zone=climate_data["climate_zone"],
            temperature=climate_data["temperature"]["annual_avg"],
            rainfall=climate_data["rainfall"]["total_mm"]
        )

        hemisphere = "southern" if location_info["latitude"] < 0 else "northern"
        sun_orientation = self._calculate_sun_orientation(
            hemisphere,
            climate_data["wind"]["prevailing_direction"]
        )

        environment_context = {
            "location": location_info["name"],
            "country": location_info["country"],
            "coordinates": {
                "latitude": location_info["latitude"],
                "longitude": location_info["longitude"]
            },
            "climate_zone": climate_data["climate_zone"],
            "temperature": climate_data["temperature"],
            "rainfall_mm": climate_data["rainfall"]["total_mm"],
            "rainfall_details": climate_data["rainfall"],
            "humidity": climate_data["humidity"]["annual_avg"],
            "prevailing_wind": climate_data["wind"]["prevailing_direction"],
            "wind_speed_ms": climate_data["wind"]["avg_speed_ms"],
            "sun_orientation": sun_orientation,
            "solar": climate_data["solar"],
            "recommendations": climate_data["recommendations"],
            "building_codes": building_codes,
            "hemisphere": hemisphere
        }

        task.progress = 100
        task.status = TaskStatus.SPEC_COMPLETE

        self.log(f"Environment analysis complete for {location_info['name']}")
        self.log(f"Climate zone: {climate_data['climate_zone']}")
        self.log(f"Annual rainfall: {climate_data['rainfall']['total_mm']}mm")

        context["environment_context"] = environment_context

        return context

    def _extract_location(self, context: Dict[str, Any]) -> Dict[str, Any]:
        specification = context["specification"]

        if isinstance(specification, dict):
            location = specification.get("location")
            if location is None:
                # Return empty location dict when location is not provided
                return {"name": "", "country": "", "latitude": 0.0, "longitude": 0.0}
            return {
                "name": location["name"],
                "country": location["country"],
                "latitude": float(location["latitude"]),
                "longitude": float(location["longitude"])
            }

        loc = specification.location
        if loc is None:
            # Return empty location dict when location is not provided
            return {"name": "", "country": "", "latitude": 0.0, "longitude": 0.0}
        return {
            "name": loc.name,
            "country": loc.country,
            "latitude": float(loc.latitude),
            "longitude": float(loc.longitude)
        }

    async def _get_building_codes_via_llm(
        self, country: str, climate_zone: str, temperature: float, rainfall: float
    ) -> Dict[str, Any]:
        prompt = f"""You are an architectural building code expert. Provide building code standards for a building in {country} with the following conditions:
- Climate Zone: {climate_zone}
- Average Temperature: {temperature}°C
- Annual Rainfall: {rainfall}mm

Return ONLY a valid JSON object (no markdown, no explanations, no backticks) with these exact fields:
{{
    "code_standard": "string",
    "minimum_ceiling_height": number,
    "minimum_window_area_ratio": number,
    "ventilation_requirement": "string",
    "roof_pitch_minimum": number,
    "elevation_minimum": number,
    "termite_protection_required": true/false,
    "earthquake_resistance": "string",
    "energy_efficiency": "string"
}}"""
        response = await self.gemini_client.generate_content(prompt)
        return response

    def _calculate_sun_orientation(self, hemisphere: str, wind_direction: str) -> Dict[str, str]:
        if hemisphere == "southern":
            return {
                "optimal_building_orientation": "east-west axis",
                "primary_windows": "north facing (sun in winter)",
                "avoid": "west facing (afternoon heat)",
                "shading_required": ["west", "northwest"],
                "sun_path": "sun travels across northern sky",
                "wind_direction": wind_direction,
                "cross_ventilation": f"optimal: {wind_direction} to opposite side"
            }
        return {
            "optimal_building_orientation": "east-west axis",
            "primary_windows": "south facing (sun in winter)",
            "avoid": "west facing (afternoon heat)",
            "shading_required": ["west", "southwest"],
            "sun_path": "sun travels across southern sky",
            "wind_direction": wind_direction,
            "cross_ventilation": f"optimal: {wind_direction} to opposite side"
        }

    def get_ifc_site_parameters(self, context: Dict[str, Any]) -> Dict[str, Any]:
        specification = context["specification"]

        location = None
        if isinstance(specification, dict):
            location = specification.get("location")
        else:
            location = specification.location

        env_context = context["environment_context"]
        building_codes = env_context["building_codes"]

        if location is None:
            # Return default values when location is not provided
            return {
                "name": "",
                "coordinates": (0.0, 0.0),
                "elevation": building_codes["elevation_minimum"],
                "climate_data": {
                    "climate_zone": env_context["climate_zone"],
                    "avg_temperature": env_context["temperature"]["annual_avg"],
                    "rainfall_mm": env_context["rainfall_mm"],
                    "humidity": env_context["humidity"]
                }
            }

        return {
            "name": location["name"],
            "coordinates": (location["latitude"], location["longitude"]),
            "elevation": building_codes["elevation_minimum"],
            "climate_data": {
                "climate_zone": env_context["climate_zone"],
                "avg_temperature": env_context["temperature"]["annual_avg"],
                "rainfall_mm": env_context["rainfall_mm"],
                "humidity": env_context["humidity"]
            }
        }
