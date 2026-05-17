import json
import re
import asyncio
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from ..core.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class ChatBotAgent:
    def __init__(self):
        self.gemini = GeminiClient()

    def _clean_json_extraction(self, text: str) -> str:
        """Extract a valid JSON object from potentially dirty response text."""
        if not text:
            return "{}"
        
        candidate = None
        # Try strict { ... } json block first
        if '{' in text and '}' in text:
            start = text.rfind('{')
            end = text.find('}', start)
            if start >= 0 and end >= start:
                candidate = text[start:end+1]
        
        if candidate and self._is_probably_valid_json(candidate):
            return candidate
        
        # Try to find a smaller json snippet if big block failed
        json_blocks = re.findall(r'\{[^{}]*\}', text)
        for blk in json_blocks:
            if self._is_probably_valid_json(blk):
                return blk
        
        # No JSON at all, return empty
        return "{}"

    def _is_probably_valid_json(self, candidate: str) -> bool:
        """Quick heuristic if the string looks like valid JSON"""
        return candidate.strip().startswith('{') and '}' in candidate and '"' in candidate[:100]

    async def process(self, prompt: str, session_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process user prompt and return chatbot response.
        Returns dict with keys: message, is_complete, specification, parsed_info, needs_questions, session_data
        
        Strategy:
        1. Ask LLM to respond in required JSON structure (system prompt)
        2. If JSON parsing fails due to non-JSON response, auto-fallback to informal plain text
        3. Never crash; always return valid JSON
        """
        if session_data is None:
            session_data = {"history": []}
        
        # Add user message to history
        history = session_data.get("history", [])
        history.append({"role": "user", "content": prompt})
        # Keep only last 6 exchanges to avoid context overload
        if len(history) > 12:
            history = history[-12:]
        
        # Build conversation context for Gemini
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
        
        system_prompt = """
Anda adalah asisten arsitektur BIM yang kompeten membantu pengguna merancang bangunan.
Anda HARUS merespons DALAM BAHASA INDONESIA kecuali pengguna meminta bahasa Inggris secara eksplisit.

Tugas Anda:
1. Memahami harapan atau pertanyaan pengguna mengenai bangunan
2. Bantu klien dengan menanyakan detail penting secara natural:
   - Jumlah lantai
   - Luas tanah (m2)
   - Jumlah dan tipe kamar (tidur, mandi, dapur, dll)
   - Lokasi bangunan
   - Gaya arsitektur
   - Fitur khusus (garasi, halaman, dll)
3. Jika informasi cukup untuk membuat spesifikasi arsitektural utuh, konfirmasilah ke pengguna.
4. Jika data belum lengkap, ajukan satu pertanyaan penjelas dalam bahasa Indonesia yang ramah.
5. Selalu jaga konteks percakapan terdahulu.

=== Wajib ===
- Nyatakan respons Anda dalam BAHASA INDONESIA nan lugas dan positif
- Gunakan struktur JSON berikut:

{
  "message": "Pesan balasan kepada pengguna",
  "is_complete": true/false,
  "specification": { ... },
  "parsed_info": { },
  "needs_questions": true/false,
  "follow_up_questions": ["pertanyaan1", "pertanyaan2"]
}

=== Catatan ===
- Jika struktur JSON tidak patuh, parsing gagal, atau respons di luar instruksi,anggap sebagai plain teks ramah.
"""
        
        full_prompt = f"{system_prompt}\n\nRiwayat percakapan:\n{history_text}\n\nAsisten:"
        
        try:
            # Call Gemini
            response_text = await self.gemini.generate_content(full_prompt)
            logger.debug(f"Raw response from LLM: {str(response_text)[:200]}...")
            
            # Attempt to parse JSON strictly — if empty or fails, treat conversation reply as plain text reasonableness
            candidate_json = self._clean_json_extraction(response_text)
            result = json.loads(candidate_json)
            
            # Ensure canonical fields
            defaults = {
                "message": "Maaf, saya kurang memahami permintaan Anda.",
                "is_complete": False,
                "specification": None,
                "parsed_info": {},
                "needs_questions": True,
                "follow_up_questions": ["Bisakah Anda menguraikan lebih rinci tentang bangunan yang Anda inginkan?"]
            }
            for k, v in defaults.items():
                result.setdefault(k, v)

        except ValueError as ve:
            # Common case: LLM returned plain Indonesian prose instead of JSON
            logger.warning(f"JSON parsing gagal, response tidak mengandung JSON valie: {ve}. Gunakan plain response LLM sebagai message.")
            result = {
                "message": response_text.strip(),
                "is_complete": False,
                "specification": None,
                "parsed_info": {},
                "needs_questions": True,
                "follow_up_questions": ["Silakan beri tambahan keterangan mengenai bangunan yang Anda maksud."]
            }
        except Exception as e:
            logger.exception(f"Unexpected error in ChatBot processing", exc_info=e)
            # Hard fallback — never expose tech stack to user
            result = {
                "message": "Maaf, terjadi gangguan internal. Silakan coba lagi nanti.",
                "is_complete": False,
                "specification": None,
                "parsed_info": {},
                "needs_questions": True,
                "follow_up_questions": ["Apakah Anda bisa mengulangi permohonan dengan sedikit perincian?"]
            }
        
        # Update session
        session_data["history"] = history
        session_data["last_response"] = result
        
        return {
            "message": result.get("message"),
            "is_complete": result.get("is_complete", False),
            "specification": result.get("specification"),
            "parsed_info": result.get("parsed_info", {}),
            "needs_questions": result.get("needs_questions", False),
            "session_data": session_data
        }


# Singleton instance
_chatbot_agent_instance: Optional[ChatBotAgent] = None


def get_chatbot_agent() -> ChatBotAgent:
    """Get or create singleton ChatBotAgent instance."""
    global _chatbot_agent_instance
    if _chatbot_agent_instance is None:
        _chatbot_agent_instance = ChatBotAgent()
        logger.info("ChatBotAgent instance created")
    return _chatbot_agent_instance
