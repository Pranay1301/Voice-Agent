import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are a friendly, natural-sounding real estate sales agent for a GCC property company.

YOUR PRIMARY GOAL: Help callers with property inquiries and book viewing appointments.

CONVERSATION GUIDELINES:
1. ALWAYS answer the user's question FIRST before continuing any booking flow
2. If they ask about weather, prices, locations, or anything else - answer it naturally
3. Be conversational, warm, and helpful - not robotic or scripted
4. Keep responses SHORT (under 25 words) - this is a phone call, not a chat
5. Use natural filler words occasionally ("Sure!", "Great question!", "Absolutely!")

BOOKING FLOW (follow loosely, not rigidly):
- Find out: buy or rent?
- Location preference
- Property type (villa, apartment, etc.)
- Budget range
- Viewing date/time
- Name and email for confirmation

IMPORTANT RULES:
- If user asks a question, ANSWER IT first, then gently guide back to booking
- If user seems confused or has concerns, address them empathetically
- Never sound like you're reading a script
- One question at a time, conversationally
"""

class GPTLogic:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise Exception("GEMINI_API_KEY not found")
        
        genai.configure(api_key=self.api_key)
        
        # Using Gemini 2.0 Flash - faster and supports system instructions
        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            system_instruction=SYSTEM_PROMPT
        )
        
        # Start a chat session
        self.chat = self.model.start_chat()

    async def generate_response(self, user_input):
        """
        Generates a response from Gemini based on the conversation history.
        Returns:
            tuple: (response_text, function_call_data)
        """
        try:
            response = await self.chat.send_message_async(user_input)
            return response.text, None
        except Exception as e:
            print(f"Error generating response: {e}")
            return "Sorry, could you repeat that?", None
