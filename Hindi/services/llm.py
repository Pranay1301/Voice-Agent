import google.generativeai as genai
from config import settings

class LLMService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.chat = self.model.start_chat(history=[])

    async def get_response(self, user_input: str):
        response = await self.chat.send_message_async(user_input)
        return response.text
