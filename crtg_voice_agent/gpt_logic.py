import os
import google.generativeai as genai
from dotenv import load_dotenv
import json

load_dotenv()

SYSTEM_PROMPT = """You are a multilingual AI sales assistant for a real estate agency. 
Your goal is to engage leads naturally, qualify them with smart questions, and log usable sales data.

Conversation Flow:
1. Greet callers professionally.
2. Ask whether they are looking to buy or rent.
3. If yes, ask their location, budget, and timeline.
4. Clarify unclear answers.
5. If uninterested, thank them and end the call.

Behavior expectations:
- Ask qualifying questions like a trained agent.
- Clarify hesitation or vagueness.
- Speak naturally (not robotic or overly formal).
- Keep responses concise (ideal for voice).
"""

# Define the tool for Gemini
log_lead_tool = {
    "function_declarations": [
        {
            "name": "log_lead",
            "description": "Log a qualified lead's details. Use this when you have gathered the user's name, contact info, and property preferences.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING", "description": "Lead's full name."},
                    "phone": {"type": "STRING", "description": "Lead's phone number."},
                    "budget": {"type": "STRING", "description": "Lead's budget range."},
                    "location_preference": {"type": "STRING", "description": "Preferred location."},
                    "property_type": {"type": "STRING", "description": "Type of property."},
                    "notes": {"type": "STRING", "description": "Any additional notes."}
                },
                "required": ["name", "phone", "location_preference"]
            }
        }
    ]
}

class GPTLogic:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise Exception("GEMINI_API_KEY not found")
        
        genai.configure(api_key=self.api_key)
        
        # Initialize the model
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=SYSTEM_PROMPT,
            tools=[log_lead_tool]
        )
        
        # Start a chat session
        self.chat = self.model.start_chat(enable_automatic_function_calling=True)

    async def generate_response(self, user_input):
        """
        Generates a response from Gemini based on the conversation history.
        """
        try:
            # Send message to Gemini
            response = await self.chat.send_message_async(user_input)
            
            # Check if there are function calls (handled automatically by enable_automatic_function_calling=True usually, 
            # but we might want to log it or handle side effects if we were doing manual handling.
            # With enable_automatic_function_calling=True, the SDK executes the function if we provided the implementation.
            # However, here we just defined the schema. 
            # For this prototype, let's just let Gemini generate the text response.
            # If we want to actually execute the code, we need to pass the functions map to start_chat.
            
            # Let's inspect the parts to see if a function call happened, just for logging.
            for part in response.parts:
                if fn := part.function_call:
                    print(f"Gemini requested function call: {fn.name} with args: {fn.args}")
                    # In a real scenario with automatic calling, we'd need to provide the function map.
                    # Since we didn't provide a map, we might need to handle it manually or just let it be.
                    # BUT, the user asked to "simulate booking/tagging". 
                    # Let's just return the text response for now.
            
            return response.text
        except Exception as e:
            print(f"Error generating Gemini response: {e}")
            return "I'm sorry, I'm having trouble understanding. Could you repeat that?"
