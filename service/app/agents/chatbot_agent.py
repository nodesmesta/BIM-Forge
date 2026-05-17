import json
import re
import asyncio
from typing import Dict, Any, Optional, List
from ..core.gemini_client import GeminiClient

class ChatBotAgent:
    def __init__(self):
        self.gemini = GeminiClient()

    async def process(self, prompt: str, session_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process user prompt and return chatbot response.
        Returns dict with keys: message, is_complete, specification, parsed_info, needs_questions, session_data
        """
        if session_data is None:
            session_data = {"history": []}
        
        # Add user message to history
        history = session_data.get("history", [])
        history.append({"role": "user", "content": prompt})
        # Keep only last 6 exchanges
        if len(history) > 12:
            history = history[-12:]
        
        # Build conversation context for Gemini
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
        
        system_prompt = """
Anda adalah asisten arsitektur BIM yang ahli dalam membantu pengguna merancang bangunan.
Anda HARUS merespons dalam bahasa Indonesia kecuali pengguna secara eksplisit meminta bahasa Inggris.
Tugas Anda:
1. Memahami permintaan pengguna dalam bahasa natural
2. Jika pengguna ingin merancang bangunan, bantu mereka dengan menanyakan detail penting seperti:
   - Jumlah lantai
   - Luas tanah atau luas bangunan
   - Jumlah dan tipe kamar (tidur, mandi, dapur, dll)
   - Lokasi bangunan
   - Gaya arsitektur yang diinginkan
   - Kebutuhan khusus (garasi, halaman, dll)
3. Jika informasi cukup untuk membuat spesifikasi bangunan, berikan pesan bahwa Anda siap membuat desain dan tanyakan konfirmasi.
4. Jika masih butuh informasi, ajukan pertanyaan penjelas satu per satu.
5. Jika pengguna hanya ingin ngobrol atau bertanya umum, jawab dengan ramah dan membantu.
6. Selalu menjaga konteks percakapan.

Format respons Anda HARUS berupa JSON dengan struktur berikut:
{
    "message": "Pesan balasan kepada pengguna dalam bahasa Indonesia",
    "is_complete": true/false,
    "specification": { /* objek spesifikasi jika is_complete=true */ },
    "parsed_info": { /* ringkasan informasi yang berhasil diekstrak dari percakapan */ },
    "needs_questions": true/false,
    "follow_up_questions": ["pertanyaan1", "pertanyaan2"] /* hanya jika needs_questions=true */
}

Jika is_complete=true, specification harus berisi minimal:
- project_name: string
- floors: integer (>=1)
- total_area_m2: number (luas tanah dalam m2)
- location: {name: string, country: string, latitude: number, longitude: number}
- style: string (misalnya "modern", "minimalis", "klasik", dll)
- rooms: array of objects dengan tipe dan jumlah kamar

Contoh specification:
{
  "project_name": "Rumah Idaman Saya",
  "floors": 2,
  "total_area_m2": 150,
  "location": {"name": "Bandung", "country": "Indonesia", "latitude": -6.9175, "longitude": 107.6191},
  "style": "minimalis",
  "rooms": [
    {"type": "bedroom", "count": 3},
    {"type": "bathroom", "count": 2},
    {"type": "kitchen", "count": 1},
    {"type": "living_room", "count": 1}
  ]
}

Jika Anda tidak yakin tentang struktur specification, set is_complete=false dan fokus pada pertanyaan penjelas.
"""
        
        full_prompt = f"{system_prompt}\n\nRiwayat percakapan:\n{history_text}\n\nAsisten:"

        try:
            # Call Gemini
            response_text = await self.gemini.generate_content(full_prompt)
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
            else:
                # If no JSON found, treat entire response as message
                result = {
                    "message": response_text.strip(),
                    "is_complete": False,
                    "specification": None,
                    "parsed_info": {},
                    "needs_questions": True,
                    "follow_up_questions": ["Bisakah Anda memberikan lebih banyak detail tentang bangunan yang Anda inginkan?"]
                }
            
            # Ensure all required fields are present and in Indonesian
            result.setdefault("message", "Maaf, saya tidak dapat memproses permintaan Anda.")
            result.setdefault("is_complete", False)
            result.setdefault("specification", None)
            result.setdefault("parsed_info", {})
            result.setdefault("needs_questions", False)
            result.setdefault("follow_up_questions", [])
            
            # If message is not Indonesian, we could translate, but we'll trust the prompt
            # However, we can do a simple check: if message contains English words and no Indonesian, we might adjust.
            # For simplicity, we rely on the system prompt.
            
            # Update session data
            session_data["history"] = history
            session_data["last_response"] = result
            
            return {
                "message": result.get("message"),
                "is_complete": result.get("is_complete", False),
                "specification": result.get("specification"),
                "parsed_info": result.get("parsed_info", {}),
                "needs_questions": result.get("needs_questions", False),
                "follow_up_questions": result.get("follow_up_questions", []),
                "session_data": session_data
            }
            
        except Exception as e:
            # Fallback response in Indonesian
            return {
                "message": f"Maaf, terjadi kesalahan dalam memproses permintaan Anda: {str(e)}",
                "is_complete": False,
                "specification": None,
                "parsed_info": {},
                "needs_questions": True,
                "follow_up_questions": ["Bisakah Anda mengulang permintaan Anda dengan cara yang berbeda?"],
                "session_data": session_data
            }


# Singleton instance
_chatbot_agent_instance: Optional[ChatBotAgent] = None


def get_chatbot_agent() -> ChatBotAgent:
    """Get or create singleton ChatBotAgent instance."""
    global _chatbot_agent_instance
    if _chatbot_agent_instance is None:
        _chatbot_agent_instance = ChatBotAgent()
    return _chatbot_agent_instance