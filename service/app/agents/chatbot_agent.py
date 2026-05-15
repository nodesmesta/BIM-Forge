"""
ChatBot Agent - Natural Language to Structured Specification Parser

This agent receives natural language descriptions and converts them into
structured ProjectSpecification format ready for IFC generation.

Unlike other workflow agents (Architect, IFC Geometry, Render), this agent
acts as the frontend interface that understands user intent.
"""

import json
import re
from typing import Dict, Any, Optional
from datetime import datetime

from ..core.gemini_client import GeminiClient
from ..core.retry_orchestrator import RetryOrchestrator
from ..models.project_specification import (
    ProjectSpecification, SiteSpecification, FloorSpecification,
    RoomRequirement, RoomType, CirculationRequirement, ZoningPreference,
    LayoutConstraints, StyleType, OrientationType
)


# City database for location context
CITY_DATA = {
    "jakarta": {"name": "Jakarta", "country": "Indonesia", "lat": -6.2, "lng": 106.8, "tz": "Asia/Jakarta"},
    "bandung": {"name": "Bandung", "country": "Indonesia", "lat": -6.9, "lng": 107.6, "tz": "Asia/Jakarta"},
    "bali": {"name": "Bali", "country": "Indonesia", "lat": -8.4, "lng": 115.1, "tz": "Asia/Makassar"},
    "surabaya": {"name": "Surabaya", "country": "Indonesia", "lat": -7.2, "lng": 112.7, "tz": "Asia/Jakarta"},
    "yogyakarta": {"name": "Yogyakarta", "country": "Indonesia", "lat": -7.8, "lng": 110.4, "tz": "Asia/Jakarta"},
    "semarang": {"name": "Semarang", "country": "Indonesia", "lat": -6.9, "lng": 110.4, "tz": "Asia/Jakarta"},
    "medan": {"name": "Medan", "country": "Indonesia", "lat": 3.6, "lng": 98.7, "tz": "Asia/Jakarta"},
    "makassar": {"name": "Makassar", "country": "Indonesia", "lat": -5.1, "lng": 119.4, "tz": "Asia/Makassar"},
    "palembang": {"name": "Palembang", "country": "Indonesia", "lat": -2.9, "lng": 104.7, "tz": "Asia/Jakarta"},
    "depok": {"name": "Depok", "country": "Indonesia", "lat": -6.4, "lng": 106.8, "tz": "Asia/Jakarta"},
    "tangerang": {"name": "Tangerang", "country": "Indonesia", "lat": -6.2, "lng": 106.6, "tz": "Asia/Jakarta"},
    "bekasi": {"name": "Bekasi", "country": "Indonesia", "lat": -6.2, "lng": 106.9, "tz": "Asia/Jakarta"},
}

STYLE_MAP = {
    "modern": StyleType.MODERN,
    "minimalis": StyleType.MINIMALIST,
    "minimalist": StyleType.MINIMALIST,
    "tropis": StyleType.TROPICAL,
    "tropical": StyleType.TROPICAL,
    "tradisional": StyleType.TRADITIONAL,
    "traditional": StyleType.TRADITIONAL,
    "industrial": StyleType.INDUSTRIAL,
}

ROOM_MAP = {
    "ruang tamu": "living_room",
    "living room": "living_room",
    "living_room": "living_room",
    "ruang makan": "dining_room",
    "dining room": "dining_room",
    "dining_room": "dining_room",
    "dapur": "kitchen",
    "kitchen": "kitchen",
    "kamar tidur": "bedroom",
    "kamar tidur biasa": "bedroom",
    "bedroom": "bedroom",
    "kamar utama": "master_bedroom",
    "master bedroom": "master_bedroom",
    "master_bedroom": "master_bedroom",
    "kamar mandi": "bathroom",
    "bathroom": "bathroom",
    "toilet": "bathroom",
    "kantor": "office",
    "office": "office",
    "studio": "office",
    "garasi": "garage",
    "garage": "garage",
    "carport": "carport",
    "car port": "carport",
    "ruang cuci": "laundry",
    "laundry": "laundry",
    "gudang": "storage",
    "storage": "storage",
    "taman": "garden",
    "garden": "garden",
    "halaman": "garden",
    "rooftop": "garden",
    "balkon": "balcony",
    "balcony": "balcony",
    "teras": "terrace",
    "terrace": "terrace",
    "hall": "hallway",
    "koridor": "hallway",
    "tangga": "staircase",
    "staircase": "staircase",
    "ruang keluarga": "living_room",
    "family room": "living_room",
}


class ChatBotAgent:
    """
    Natural language chatbot agent that converts user descriptions
    into structured building specifications.
    
    This agent:
    1. Receives natural language input from user
    2. Parses and extracts building requirements
    3. Generates a complete ProjectSpecification
    4. Returns structured data ready for IFC generation
    """
    
    def __init__(self):
        self.client = GeminiClient()
        self.retry = RetryOrchestrator()
        self.name = "ChatBot Agent"
        self.description = "Natural language to structured specification parser"
    
    def _parse_natural_language(self, prompt: str) -> Dict[str, Any]:
        """
        Parse natural language prompt using regex patterns.
        Fast, deterministic parsing without LLM.
        """
        text = prompt.lower()
        
        # Parse floors
        floor_match = re.search(r'(\d+)\s*(?:lantai|floor|storey|tingkat)', text)
        floors = int(floor_match.group(1)) if floor_match else 1
        
        # Parse style
        style = "modern"
        for style_name, style_enum in STYLE_MAP.items():
            if style_name in text:
                style = style_name
                break
        
        # Parse location
        location = None
        for city_key, city_data in CITY_DATA.items():
            if city_key in text:
                location = {
                    "name": city_data["name"],
                    "country": city_data["country"],
                    "latitude": city_data["lat"],
                    "longitude": city_data["lng"],
                    "timezone": city_data["tz"],
                }
                break
        
        # Parse rooms with counts
        rooms = []
        found_rooms = set()
        
        # Check for room patterns in order (longer patterns first)
        sorted_room_patterns = sorted(ROOM_MAP.keys(), key=len, reverse=True)
        
        for pattern in sorted_room_patterns:
            if pattern in text and pattern not in found_rooms:
                room_type = ROOM_MAP[pattern]
                
                # Try to find count for this room type
                # Pattern: "3 kamar tidur", "x3 bedroom", "3x bedroom"
                count_match = re.search(
                    rf'(\d+)\s*(?:buah|unit|x|×)?\s*{re.escape(pattern)}',
                    text
                )
                if not count_match:
                    count_match = re.search(
                        rf'{re.escape(pattern)}\s*(?:x|×)?\s*(\d+)',
                        text
                    )
                
                count = int(count_match.group(1)) if count_match else 1
                
                # Default areas based on room type
                default_areas = {
                    "living_room": 20,
                    "dining_room": 16,
                    "kitchen": 9,
                    "bedroom": 12,
                    "master_bedroom": 16,
                    "bathroom": 6,
                    "office": 12,
                    "garage": 20,
                    "carport": 15,
                    "laundry": 6,
                    "storage": 6,
                    "garden": 20,
                    "balcony": 8,
                    "terrace": 15,
                    "hallway": 8,
                    "staircase": 6,
                }
                
                # Determine preferred floor based on room privacy
                is_private = room_type in ["bedroom", "master_bedroom", "bathroom", "office"]
                preferred_floor = 2 if (floors > 1 and is_private) else 1
                
                rooms.append({
                    "room_type": room_type,
                    "count": count,
                    "min_width_m": 3.5,
                    "min_length_m": 3.5,
                    "min_area_m2": default_areas.get(room_type, 12),
                    "preferred_floor": preferred_floor,
                    "adjacent_to": [],
                    "exterior_access": room_type in ["garage", "carport", "garden"],
                    "private": is_private,
                })
                
                found_rooms.add(pattern)
        
        # If no rooms found, add default living room
        if not rooms:
            rooms.append({
                "room_type": "living_room",
                "count": 1,
                "min_width_m": 4,
                "min_length_m": 4,
                "min_area_m2": 20,
                "preferred_floor": 1,
                "adjacent_to": [],
                "exterior_access": False,
                "private": False,
            })
        
        # Parse total area if mentioned
        area_match = re.search(r'(\d+)\s*(?:m2|m²|meter\s*persegi|persegi)', text)
        if area_match:
            total_area = float(area_match.group(1))
        else:
            # Estimate from rooms
            total_area = sum(r["min_area_m2"] * r["count"] for r in rooms) * 1.4
        
        # Generate project name
        style_label = style.capitalize()
        floors_label = f"{floors} Lantai" if floors > 1 else "1 Lantai"
        location_label = f" di {location['name']}" if location else ""
        project_name = f"Rumah {style_label} {floors_label}{location_label}"
        
        return {
            "project_name": project_name,
            "style": style,
            "location": location,
            "floors": floors,
            "rooms": rooms,
            "total_area": total_area,
        }
    
    def _create_specification(self, parsed: Dict[str, Any]) -> ProjectSpecification:
        """Convert parsed data to ProjectSpecification."""
        floors = parsed["floors"]
        area = parsed["total_area"]
        building_area = area * 0.8
        
        # Build floor specifications
        floor_specs = []
        for i in range(1, floors + 1):
            floor_specs.append(FloorSpecification(
                floor_number=i,
                height_m=3.5 if i == 1 else 3.2,
                ceiling_height_m=3.0 if i == 1 else 2.8,
                slab_thickness_m=0.15,
                purpose="public" if i == 1 else "private"
            ))
        
        # Build room requirements
        room_specs = []
        for room_data in parsed["rooms"]:
            try:
                room_type = RoomType(room_data["room_type"])
            except ValueError:
                room_type = RoomType.LIVING_ROOM
            
            room_specs.append(RoomRequirement(
                room_type=room_type,
                count=room_data["count"],
                min_width_m=room_data["min_width_m"],
                min_length_m=room_data["min_length_m"],
                min_area_m2=room_data["min_area_m2"],
                preferred_floor=room_data["preferred_floor"],
                adjacent_to=room_data["adjacent_to"],
                exterior_access=room_data["exterior_access"],
                private=room_data["private"]
            ))
        
        return ProjectSpecification(
            project_name=parsed["project_name"],
            style=STYLE_MAP.get(parsed["style"], StyleType.MODERN),
            location=None,  # Will be set if parsed
            site=SiteSpecification(
                total_land_area_m2=area * 1.3,
                building_footprint_m2=building_area,
                building_width_m=max(8, building_area / 10),
                building_depth_m=building_area / max(8, building_area / 10),
                orientation=OrientationType.NORTH,
                setback_north_m=3,
                setback_south_m=2,
                setback_east_m=2,
                setback_west_m=2,
                slope_degree=0,
                shape_id="rectangle",
                shape_dimensions={
                    "width": max(8, building_area / 10),
                    "depth": building_area / max(8, building_area / 10)
                }
            ),
            floors=floor_specs,
            rooms=room_specs,
            circulation=CirculationRequirement(
                corridor_width_m=1.2,
                staircase_width_m=1.2,
                staircase_type="straight" if floors > 1 else "straight",
                elevator=(floors > 3)
            ),
            zoning=ZoningPreference(
                public=["living_room", "dining_room", "kitchen"],
                private=["bedroom", "master_bedroom", "bathroom"],
                service=["laundry", "storage", "garage"]
            ),
            constraints=LayoutConstraints(
                entrance_position="front_center",
                kitchen_location="rear",
                master_bedroom_location="rear_corner"
            )
        )
    
    async def process(self, prompt: str) -> Dict[str, Any]:
        """
        Main entry point: Process natural language prompt into specification.
        
        Args:
            prompt: Natural language description from user
            
        Returns:
            Dictionary containing:
            - success: bool
            - specification: ProjectSpecification (as dict)
            - parsed_info: Dict with parsed components for display
            - message: Status message
        """
        if not prompt or not prompt.strip():
            return {
                "success": False,
                "message": "Prompt tidak boleh kosong",
                "specification": None,
                "parsed_info": None
            }
        
        try:
            # Step 1: Fast regex parsing
            parsed = self._parse_natural_language(prompt)
            
            # Step 2: Create specification object
            spec = self._create_specification(parsed)
            
            # Step 3: Create LocationInfo if location found
            from ..models.project_specification import LocationInfo
            if parsed.get("location"):
                spec.location = LocationInfo(**parsed["location"])
            
            return {
                "success": True,
                "message": f"Berhasil memproses prompt: {parsed['project_name']}",
                "specification": spec.model_dump(),
                "parsed_info": {
                    "project_name": parsed["project_name"],
                    "style": parsed["style"],
                    "floors": parsed["floors"],
                    "rooms": parsed["rooms"],
                    "location": parsed.get("location"),
                    "total_area": parsed["total_area"]
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Gagal memproses prompt: {str(e)}",
                "specification": None,
                "parsed_info": None
            }
    
    def get_room_summary(self, rooms: list) -> str:
        """Generate a human-readable summary of rooms."""
        summary_parts = []
        room_counts = {}
        
        for room in rooms:
            room_type = room.get("room_type", "unknown")
            count = room.get("count", 1)
            room_counts[room_type] = room_counts.get(room_type, 0) + count
        
        room_labels = {
            "living_room": "Ruang Tamu",
            "dining_room": "Ruang Makan",
            "kitchen": "Dapur",
            "bedroom": "Kamar Tidur",
            "master_bedroom": "Kamar Utama",
            "bathroom": "Kamar Mandi",
            "office": "Kantor",
            "garage": "Garasi",
            "carport": "Carport",
            "laundry": "Ruang Cuci",
            "storage": "Gudang",
            "garden": "Taman",
        }
        
        for room_type, count in room_counts.items():
            label = room_labels.get(room_type, room_type.replace("_", " ").title())
            if count > 1:
                summary_parts.append(f"{count}x {label}")
            else:
                summary_parts.append(label)
        
        return ", ".join(summary_parts)


# Singleton instance
_chatbot_agent: Optional[ChatBotAgent] = None

def get_chatbot_agent() -> ChatBotAgent:
    """Get the singleton ChatBotAgent instance."""
    global _chatbot_agent
    if _chatbot_agent is None:
        _chatbot_agent = ChatBotAgent()
    return _chatbot_agent