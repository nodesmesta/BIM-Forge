"""
ChatBot Agent - Intelligent Assistant with Intent Detection

This agent uses LLM to:
1. Classify user intent (building_design vs general_chat)
2. For building_design: parse and build specifications conversationally
3. For general_chat: respond naturally in whatever language feels right
4. No forced language — LLM decides response language naturally
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from ..core.gemini_client import GeminiClient


# Required fields schema for building specification
REQUIRED_FIELDS = {
    "project_name": {"type": "string", "required": True, "description": "Nama proyek bangunan"},
    "style": {"type": "enum", "required": True, "values": ["modern", "minimalist", "tropical", "traditional", "industrial"], "description": "Gaya arsitektur"},
    "floors": {"type": "int", "required": True, "min": 1, "max": 10, "description": "Jumlah lantai"},
    "rooms": {"type": "array", "required": True, "description": "Daftar ruangan dengan minimal 1 ruang tamu"},
    "location": {"type": "object", "required": False, "description": "Lokasi bangunan (kota Indonesia)"},
    "total_area": {"type": "float", "required": False, "description": "Luas total bangunan dalam m2"},
}

ROOM_TYPES = [
    "living_room", "dining_room", "kitchen", "bedroom", "master_bedroom",
    "bathroom", "office", "garage", "carport", "laundry", "storage",
    "garden", "balcony", "terrace"
]

STYLE_TYPES = ["modern", "minimalist", "tropical", "traditional", "industrial"]

CITY_DATA = {
    "jakarta": {"name": "Jakarta", "country": "Indonesia", "lat": -6.2, "lng": 106.8, "tz": "Asia/Jakarta"},
    "bandung": {"name": "Bandung", "country": "Indonesia", "lat": -6.9, "lng": 107.6, "tz": "Asia/Jakarta"},
    "bali": {"name": "Bali", "country": "Indonesia", "lat": -8.4, "lng": 115.1, "tz": "Asia/Makassar"},
    "surabaya": {"name": "Surabaya", "country": "Indonesia", "lat": -7.2, "lng": 112.7, "tz": "Asia/Jakarta"},
    "yogyakarta": {"name": "Yogyakarta", "country": "Indonesia", "lat": -7.8, "lng": 110.4, "tz": "Asia/Jakarta"},
    "semarang": {"name": "Semarang", "country": "Indonesia", "lat": -6.9, "lng": 110.4, "tz": "Asia/Jakarta"},
    "medan": {"name": "Medan", "country": "Indonesia", "lat": 3.6, "lng": 98.7, "tz": "Asia/Jakarta"},
    "makassar": {"name": "Makassar", "country": "Indonesia", "lat": -5.1, "lng": 119.4, "tz": "Asia/Makassar"},
    "depok": {"name": "Depok", "country": "Indonesia", "lat": -6.4, "lng": 106.8, "tz": "Asia/Jakarta"},
    "tangerang": {"name": "Tangerang", "country": "Indonesia", "lat": -6.2, "lng": 106.6, "tz": "Asia/Jakarta"},
    "bekasi": {"name": "Bekasi", "country": "Indonesia", "lat": -6.2, "lng": 106.9, "tz": "Asia/Jakarta"},
}


class SpecificationBuilder:
    """Tracks building specification state during conversation."""

    def __init__(self):
        self.data: Dict[str, Any] = {
            "project_name": None,
            "style": None,
            "floors": None,
            "rooms": [],
            "location": None,
            "total_area": None,
        }
        self.missing_fields: List[str] = []
        self.conversation_history: List[Dict[str, str]] = []

    def to_specification(self) -> Dict[str, Any]:
        """Convert to complete specification format."""
        floors = self.data.get("floors", 1)
        area = self.data.get("total_area") or self._estimate_area()
        building_area = area * 0.8

        # Build floors
        floor_specs = []
        for i in range(1, floors + 1):
            floor_specs.append({
                "floor_number": i,
                "height_m": 3.5 if i == 1 else 3.2,
                "ceiling_height_m": 3.0 if i == 1 else 2.8,
                "slab_thickness_m": 0.15,
                "purpose": "public" if i == 1 else "private"
            })

        # Process rooms
        room_specs = []
        for room in self.data.get("rooms", []):
            room_type = room.get("room_type", "living_room")
            is_private = room_type in ["bedroom", "master_bedroom", "bathroom", "office"]
            preferred_floor = 2 if (floors > 1 and is_private) else 1

            room_specs.append({
                "room_type": room_type,
                "count": room.get("count", 1),
                "min_width_m": room.get("min_width_m", 3.5),
                "min_length_m": room.get("min_length_m", 3.5),
                "min_area_m2": room.get("min_area_m2", 12),
                "preferred_floor": preferred_floor,
                "adjacent_to": room.get("adjacent_to", []),
                "exterior_access": room_type in ["garage", "carport", "garden"],
                "private": is_private
            })

        return {
            "project_name": self.data.get("project_name", "Rumah Tanpa Nama"),
            "style": self.data.get("style", "modern"),
            "location": self.data.get("location"),
            "site": {
                "total_land_area_m2": area * 1.3,
                "building_footprint_m2": building_area,
                "building_width_m": max(8, building_area / 10),
                "building_depth_m": building_area / max(8, building_area / 10),
                "orientation": "north",
                "setback_north_m": 3.0,
                "setback_south_m": 2.0,
                "setback_east_m": 2.0,
                "setback_west_m": 2.0,
                "slope_degree": 0.0
            },
            "floors": floor_specs,
            "rooms": room_specs,
            "circulation": {
                "corridor_width_m": 1.2,
                "staircase_width_m": 1.2,
                "staircase_type": "straight" if floors > 1 else "straight",
                "elevator": floors > 3
            },
            "zoning": {
                "public": ["living_room", "dining_room", "kitchen"],
                "private": ["bedroom", "master_bedroom"],
                "service": ["bathroom", "laundry", "storage"]
            },
            "constraints": {
                "entrance_position": "front_center",
                "kitchen_location": "rear",
                "master_bedroom_location": "rear_corner"
            }
        }

    def _estimate_area(self) -> float:
        """Estimate total area from rooms."""
        total = 0
        for room in self.data.get("rooms", []):
            area = room.get("min_area_m2", 12)
            count = room.get("count", 1)
            total += area * count
        return max(total * 1.4, 50)

    def is_complete(self) -> bool:
        """Check if specification is complete enough to generate."""
        return (
            self.data.get("project_name") is not None and
            self.data.get("style") is not None and
            self.data.get("floors") is not None and
            len(self.data.get("rooms", [])) > 0
        )

    def get_missing_fields(self) -> List[str]:
        """Return list of missing required fields."""
        missing = []
        if not self.data.get("project_name"):
            missing.append("project_name")
        if not self.data.get("style"):
            missing.append("style")
        if not self.data.get("floors"):
            missing.append("floors")
        if len(self.data.get("rooms", [])) == 0:
            missing.append("rooms")
        return missing


class ChatBotAgent:
    """
    Intelligent assistant with intent detection.

    Detects user intent and routes accordingly:
    - building_design: Build specifications through conversation
    - general_chat: Natural free-form response
    """

    def __init__(self):
        self.client = GeminiClient()
        self.name = "ChatBot Agent"
        self.description = "Intelligent assistant with intent detection"

    async def _detect_intent(self, prompt: str, session_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Classify user intent using LLM.

        Returns one of: building_design, general_chat
        If session already has builder_data (mid-spec conversation), always return building_design.
        """
        # If we're already in a building specification session, stay in that flow
        if session_data and session_data.get("builder_data"):
            return "building_design"

        system_prompt = """You are an intent classifier. Classify the user message into one of two categories:

1. "building_design" - User wants to design/describe a building, house, or architectural project. Keywords: rumah, house, building, gedung, bangunan, desain, design, arsitektur, lantai, floors, kamar, rooms, bedroom, bathroom, kitchen, dapur, etc. Also includes follow-up questions about a building project they're working on.

2. "general_chat" - Everything else: greetings, questions about capabilities, small talk, technical questions not about building design, etc.

Return ONLY a JSON object:
{"intent": "building_design"|"general_chat", "reasoning": "brief one-line explanation"}"""

        try:
            result = await self.client._make_request({
                "contents": [{
                    "role": "user",
                    "parts": [{"text": f"{system_prompt}\n\nUser message: {prompt}"}]
                }],
                "generationConfig": {
                    "temperature": 0.0,
                    "maxOutputTokens": 256
                }
            })

            intent = result.get("intent", "general_chat")
            return intent

        except Exception:
            # Fallback: check for building keywords
            building_keywords = [
                "rumah", "house", "building", "gedung", "bangunan",
                "lantai", "floor", "kamar", "room", "bedroom", "bathroom",
                "dapur", "kitchen", "desain", "design", "arsitek",
                "minimalis", "modern", "tropis", "industrial"
            ]
            prompt_lower = prompt.lower()
            for kw in building_keywords:
                if kw in prompt_lower:
                    return "building_design"
            return "general_chat"

    async def _handle_general_chat(self, prompt: str, session_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle general conversation - LLM responds naturally.
        No forced building context, no forced language.
        """
        # Build conversation history from session
        history = []
        if session_data and session_data.get("history"):
            history = session_data.get("history", [])

        system_prompt = """You are a helpful, knowledgeable assistant integrated into a BIM (Building Information Modeling) platform called BIM Forge. 

You can help with:
- Building design and architecture (just ask naturally!)
- Questions about BIM, IFC, 3D modeling
- Technical questions about construction and engineering
- General conversation and assistance

Respond naturally and conversationally. Use whatever language feels most natural for the context - if the user speaks Indonesian, respond in Indonesian. If they speak English, respond in English. Don't force a particular language.

Be friendly and concise. If the user seems interested in building design, gently invite them to describe what they want to build."""

        # Build messages array
        contents = []

        for entry in history[-10:]:  # Last 10 messages for context
            role = "model" if entry.get("role") == "assistant" else "user"
            contents.append({
                "role": role,
                "parts": [{"text": entry.get("content", "")}]
            })

        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        try:
            result = await self.client._make_text_request({
                "contents": contents,
                "systemInstruction": {
                    "parts": [{"text": system_prompt}]
                },
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 2048
                }
            })

            response_text = result if isinstance(result, str) else str(result)

            # Update history
            new_history = history + [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response_text}
            ]

            return {
                "message": response_text,
                "is_complete": False,
                "specification": None,
                "parsed_info": {
                    "intent": "general_chat"
                },
                "session_data": {
                    "builder_data": None,
                    "history": new_history
                },
                "needs_questions": False,
                "intent": "general_chat"
            }

        except Exception as e:
            return {
                "message": f"I'm having trouble responding right now. Could you try again?",
                "is_complete": False,
                "specification": None,
                "parsed_info": {"intent": "general_chat"},
                "session_data": {
                    "builder_data": None,
                    "history": history
                },
                "needs_questions": False,
                "intent": "general_chat"
            }

    async def _parse_initial_prompt(self, prompt: str) -> Dict[str, Any]:
        """Use LLM to parse initial prompt and extract building requirements."""

        system_prompt = """You are a friendly architect assistant helping someone plan their building. Be conversational and helpful.

Parse the user's building description and extract information in JSON format.

Extract these fields:
- project_name: A suitable name for the project
- style: One of [modern, minimalist, tropical, traditional, industrial]
- floors: Number of floors (integer)
- rooms: Array of rooms, each with:
  - room_type: One of [living_room, dining_room, kitchen, bedroom, master_bedroom, bathroom, office, garage, carport, laundry, storage, garden, balcony, terrace]
  - count: Number of this room type
  - min_area_m2: Minimum area in square meters (defaults: living_room=20, dining_room=16, kitchen=9, bedroom=12, master_bedroom=18, bathroom=6, office=12, garage=20, carport=15)
- location: Object with {name, country, latitude, longitude, timezone} if city is mentioned
- total_area: Estimated total building area in m2 if mentioned

Return ONLY valid JSON, no other text."""

        full_prompt = f"{system_prompt}\n\nUser input: {prompt}"

        try:
            result = await self.client._make_request({
                "contents": [{
                    "role": "user",
                    "parts": [{"text": full_prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 4096
                }
            })

            # Validate and clean result
            parsed = {
                "project_name": result.get("project_name"),
                "style": result.get("style", "modern"),
                "floors": result.get("floors", 1),
                "rooms": result.get("rooms", []),
                "location": result.get("location"),
                "total_area": result.get("total_area")
            }

            return parsed

        except Exception as e:
            # Fallback to simple regex parsing
            return self._fallback_parse(prompt)

    def _fallback_parse(self, prompt: str) -> Dict[str, Any]:
        """Simple fallback parsing when LLM fails."""
        import re

        text = prompt.lower()

        # Parse floors
        floor_match = re.search(r'(\d+)\s*(?:lantai|floor|storey|tingkat)', text)
        floors = int(floor_match.group(1)) if floor_match else 1

        # Parse style
        style = "modern"
        for s in STYLE_TYPES:
            if s in text:
                style = s
                break
        if "tropis" in text:
            style = "tropical"
        elif "tradisional" in text:
            style = "traditional"

        # Parse rooms
        rooms = []
        room_patterns = {
            "kamar tidur": ("bedroom", 12),
            "bedroom": ("bedroom", 12),
            "kamar utama": ("master_bedroom", 18),
            "master bedroom": ("master_bedroom", 18),
            "kamar mandi": ("bathroom", 6),
            "bathroom": ("bathroom", 6),
            "ruang tamu": ("living_room", 20),
            "living room": ("living_room", 20),
            "ruang makan": ("dining_room", 16),
            "dining room": ("dining_room", 16),
            "dapur": ("kitchen", 9),
            "kitchen": ("kitchen", 9),
            "kantor": ("office", 12),
            "office": ("office", 12),
            "garasi": ("garage", 20),
            "garage": ("garage", 20),
            "carport": ("carport", 15),
        }

        for pattern, (room_type, area) in room_patterns.items():
            if pattern in text:
                count_match = re.search(rf'(\d+)\s*{pattern}', text)
                count = int(count_match.group(1)) if count_match else 1
                rooms.append({
                    "room_type": room_type,
                    "count": count,
                    "min_area_m2": area
                })

        # Parse location
        location = None
        for city_key, city_data in CITY_DATA.items():
            if city_key in text:
                location = city_data
                break

        # Generate project name
        location_label = f" di {location['name']}" if location else ""
        project_name = f"Rumah {style.capitalize()} {floors} Lantai{location_label}"

        return {
            "project_name": project_name,
            "style": style,
            "floors": floors,
            "rooms": rooms if rooms else [{"room_type": "living_room", "count": 1, "min_area_m2": 20}],
            "location": location,
            "total_area": None
        }

    async def _identify_missing_info(self, builder: SpecificationBuilder, user_message: str) -> Dict[str, Any]:
        """Use LLM to identify what's missing and generate clarifying questions."""

        missing = builder.get_missing_fields()

        if not missing:
            return {"type": "complete", "questions": []}

        # Generate specific questions for missing fields
        questions_prompt = f"""The user is planning a building and we need more information to complete the specification.

Current partial info:
{json.dumps(builder.data, indent=2)}

Missing fields: {missing}

Ask 1 simple question to gather the most important missing info. Be casual and conversational. Respond in the same language the user has been using.

Return JSON:
{{
  "questions": ["your one question here"],
  "reasoning": "brief explanation"
}}

Return ONLY valid JSON."""

        try:
            result = await self.client._make_request({
                "contents": [{
                    "role": "user",
                    "parts": [{"text": questions_prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 1024
                }
            })

            return {
                "type": "incomplete",
                "questions": result.get("questions", []),
                "missing_fields": missing
            }

        except Exception as e:
            # Fallback questions
            return self._fallback_questions(missing)

    def _fallback_questions(self, missing: List[str]) -> Dict[str, Any]:
        """Generate fallback questions when LLM fails."""
        questions = []

        if "style" in missing:
            questions.append("What architectural style are you going for? (modern, minimalist, tropical, traditional)")
        if "floors" in missing:
            questions.append("How many floors does the building have?")
        if "rooms" in missing:
            questions.append("What rooms do you need? (bedrooms, bathrooms, kitchen, etc.)")
        if "project_name" in missing:
            questions.append("What would you like to call this project?")

        return {
            "type": "incomplete",
            "questions": [questions[0]] if questions else [],
            "missing_fields": missing
        }

    async def _update_from_user_response(self, builder: SpecificationBuilder, user_response: str) -> Dict[str, Any]:
        """Use LLM to extract information from user response."""

        prompt = f"""Extract building specification information from the user's response.

User response: {user_response}

Current partial specification:
{json.dumps(builder.data, indent=2)}

Extract any new or updated information and return as JSON with only the changed/added fields.

Return JSON with the fields that can be extracted from the response:
{{
  "project_name": "updated name if mentioned",
  "style": "updated style if mentioned",
  "floors": updated floor count if mentioned,
  "rooms": [updated/added rooms array if mentioned],
  "location": {{
    "name": "city name if mentioned",
    "country": "Indonesia",
    "latitude": number if mentioned,
    "longitude": number if mentioned,
    "timezone": "Asia/Jakarta"
  }},
  "total_area": number if mentioned
}}

Only include fields that are explicitly mentioned in the response. Return ONLY valid JSON."""

        try:
            result = await self.client._make_request({
                "contents": [{
                    "role": "user",
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 2048
                }
            })

            # Update builder with extracted data
            for key, value in result.items():
                if value is not None:
                    if key == "rooms" and isinstance(value, list):
                        # Merge rooms
                        existing_types = {r["room_type"] for r in builder.data.get("rooms", [])}
                        for room in value:
                            if room.get("room_type") not in existing_types:
                                builder.data.setdefault("rooms", []).append(room)
                    else:
                        builder.data[key] = value

            return {"success": True, "updated": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _format_specification_summary(self, builder: SpecificationBuilder) -> str:
        """Format specification for display."""
        data = builder.data
        rooms = data.get("rooms", [])

        room_labels = {
            "living_room": "Living Room",
            "dining_room": "Dining Room",
            "kitchen": "Kitchen",
            "bedroom": "Bedroom",
            "master_bedroom": "Master Bedroom",
            "bathroom": "Bathroom",
            "office": "Office",
            "garage": "Garage",
            "carport": "Carport",
            "laundry": "Laundry",
            "storage": "Storage",
            "garden": "Garden",
            "balcony": "Balcony",
            "terrace": "Terrace",
        }

        style_labels = {
            "modern": "Modern",
            "minimalist": "Minimalist",
            "tropical": "Tropical",
            "traditional": "Traditional",
            "industrial": "Industrial",
        }

        # Summarize rooms
        room_counts = {}
        for room in rooms:
            rt = room.get("room_type", "unknown")
            cnt = room.get("count", 1)
            room_counts[rt] = room_counts.get(rt, 0) + cnt

        room_summary = []
        for rt, cnt in room_counts.items():
            label = room_labels.get(rt, rt)
            room_summary.append(f"- {cnt}x {label}")

        location_text = data.get('location', {}).get('name', 'Not specified') if data.get('location') else 'Not specified'

        summary = f"""Great! Here's what I've got so far:

**Project:** {data.get('project_name', 'Untitled')}
**Style:** {style_labels.get(data.get('style', 'modern'), data.get('style', 'modern').capitalize())}
**Floors:** {data.get('floors', 1)}
**Location:** {location_text}
**Estimated Size:** ~{int(builder._estimate_area())}m²

**Rooms:**
{chr(10).join(room_summary) if room_summary else '- None added yet'}

Ready to generate when you are! Click the **Generate** button below to create your building model."""

        return summary

    async def process(self, prompt: str, session_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main entry point for processing user input.

        Detects intent and routes to appropriate handler.

        Args:
            prompt: User's message
            session_data: Optional session state with builder and history

        Returns:
            Dict with:
            - message: Response to show user
            - is_complete: Whether specification is ready
            - specification: Complete spec if is_complete=True
            - session_data: Updated session state for next turn
            - needs_questions: Whether we need more info
            - intent: Detected intent (building_design / general_chat)
        """
        # Step 0: Detect intent
        is_first_message = not session_data or not session_data.get("builder_data")

        if is_first_message:
            intent = await self._detect_intent(prompt, session_data)

            if intent == "general_chat":
                return await self._handle_general_chat(prompt, session_data)

            # intent == "building_design" - proceed to specification flow
            intent = "building_design"
        else:
            intent = "building_design"

        # Initialize or restore session
        if session_data and "builder_data" in session_data and session_data["builder_data"]:
            builder = SpecificationBuilder()
            builder.data = session_data.get("builder_data", {})
            builder.conversation_history = session_data.get("history", [])
        else:
            builder = SpecificationBuilder()

        # Add user message to history
        builder.conversation_history.append({"role": "user", "content": prompt})

        # Step 1: Parse/update specification from user input
        is_first_turn = len([m for m in builder.conversation_history if m["role"] == "user"]) == 1

        if is_first_turn and not builder.data.get("project_name"):
            # First building design message - parse initial prompt
            parsed = await self._parse_initial_prompt(prompt)
            for key, value in parsed.items():
                if value is not None:
                    builder.data[key] = value
        else:
            # Subsequent messages - update from response
            await self._update_from_user_response(builder, prompt)

        # Step 2: Check if specification is complete
        if builder.is_complete():
            specification = builder.to_specification()

            # Add assistant response to history
            builder.conversation_history.append({
                "role": "assistant",
                "content": self._format_specification_summary(builder)
            })

            return {
                "message": self._format_specification_summary(builder),
                "is_complete": True,
                "specification": specification,
                "parsed_info": {
                    "project_name": builder.data.get("project_name"),
                    "style": builder.data.get("style"),
                    "floors": builder.data.get("floors"),
                    "rooms": builder.data.get("rooms", []),
                    "location": builder.data.get("location"),
                    "total_area": builder._estimate_area()
                },
                "session_data": {
                    "builder_data": builder.data,
                    "history": builder.conversation_history
                },
                "needs_questions": False,
                "intent": intent
            }

        # Step 3: Ask for missing information
        missing_info = await self._identify_missing_info(builder, prompt)
        questions = missing_info.get("questions", [])

        if questions:
            main_question = questions[0] if questions else None
            if main_question:
                message = main_question
            else:
                message = "Bisa ceritakan lebih detail tentang bangunan yang Anda inginkan?"
        else:
            message = "Saya belum yakin paham. Bisa deskripsikan bangunan yang Anda inginkan?"

        # Add assistant response to history
        builder.conversation_history.append({
            "role": "assistant",
            "content": message
        })

        return {
            "message": message,
            "is_complete": False,
            "specification": None,
            "parsed_info": {
                "project_name": builder.data.get("project_name"),
                "style": builder.data.get("style"),
                "floors": builder.data.get("floors"),
                "rooms": builder.data.get("rooms", []),
                "location": builder.data.get("location"),
                "total_area": builder._estimate_area() if builder.data.get("rooms") else None
            },
            "session_data": {
                "builder_data": builder.data,
                "history": builder.conversation_history
            },
            "needs_questions": True,
            "intent": intent
        }


# Singleton instance
_chatbot_agent: Optional[ChatBotAgent] = None

def get_chatbot_agent() -> ChatBotAgent:
    """Get the singleton ChatBotAgent instance."""
    global _chatbot_agent
    if _chatbot_agent is None:
        _chatbot_agent = ChatBotAgent()
    return _chatbot_agent