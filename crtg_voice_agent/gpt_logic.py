import os
import json
import logging
from typing import Optional, Tuple, Dict, Any
from groq import Groq, APIError, RateLimitError, InternalServerError
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import caching
from utils.response_cache import response_cache

SYSTEM_PROMPT = """You are a friendly, human-like real estate assistant.

CORE PERSONA:
- Tone: Casual but professional. Warm and approachable.
- Speak naturally, like a human. Use fillers like "I see", "Got it", "Okay" occasionally.
- AVOID robotic repetition. Vary your phrasing.

CRITICAL RULES:
1. Ask ONLY ONE question per turn. Never ask two questions in a row.
2. Wait for the user's answer after every question.
3. Keep responses brief (under 20 words).

HANDLING UNRELATED INPUTS:
If the user gives an answer that does NOT fit the current step (e.g., "I like blue" when asked for budget, or "What is the weather?" when asked for location):
1. Briefly acknowledge or deflect (e.g., "I can't help with that, but...", "I understand, however...").
2. RE-ASK the CURRENT step's question.
3. Do NOT proceed to the next step.

BOOKING FLOW (one step at a time):
Step 1: "Are you looking to buy or rent?"
Step 2: "Which area are you interested in?"
Step 3: "What type of property - villa, apartment, or penthouse?"
Step 4: "What's your budget range?"
Step 5: "When would you like to view?" (MUST be a time/date. If not, ask again).
Step 6: "May I have your name please?"
Step 7: "And your email address?"
Step 8: "Thank you. Your viewing is confirmed."

FOR NAMES: "Got it, [Name]. And your email address?"
FOR EMAILS: Spell it back: "That's P-R-A-N-A-Y at gmail dot com?"

Review your response: If it contains more than one question, DELETE the second one.
"""

class GPTLogic:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in .env")
        
        self.client = Groq(api_key=self.api_key)
        self.conversation_history = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.max_history_length = 20  # Limit conversation history to prevent context bloat
        self.validation_rules = {
            "name": r"^[A-Za-z\s]{2,50}$",
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "budget": r"^\d{3,8}$",
            "location": r"^[A-Za-z\s]{2,100}$"
        }

    def _validate_input(self, user_input: str, field_type: Optional[str] = None) -> bool:
        """Validate user input based on field type."""
        if not user_input or not user_input.strip():
            return False
        
        user_input = user_input.strip()
        
        if field_type == "name":
            import re
            return bool(re.match(self.validation_rules["name"], user_input))
        elif field_type == "email":
            import re
            return bool(re.match(self.validation_rules["email"], user_input))
        elif field_type == "budget":
            import re
            return bool(re.match(self.validation_rules["budget"], user_input))
        elif field_type == "location":
            import re
            return bool(re.match(self.validation_rules["location"], user_input))
        
        return True

    def _sanitize_response(self, response: str) -> str:
        """Sanitize and validate GPT response to prevent hallucination."""
        if not response:
            return "I didn't catch that. Could you please repeat?"
        
        # Remove any markdown formatting
        response = response.replace("*", "").replace("_", "").replace("#", "")
        
        # Limit response length
        if len(response.split()) > 20:
            response = " ".join(response.split()[:20]) + "..."
        
        # Ensure response contains only one question
        question_count = response.count("?")
        if question_count > 1:
            # Take only the first question
            first_question = response.split("?")[0] + "?"
            response = first_question
        
        # Remove any mentions of specific properties or prices
        response = response.replace("$", "").replace("₹", "")
        
        return response.strip()

    def _extract_structured_data(self, user_input: str) -> Dict[str, Any]:
        """Extract structured data from user input."""
        import re
        data = {}
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
        email_match = re.search(email_pattern, user_input)
        if email_match:
            data["email"] = email_match.group()
        
        # Extract name (simple heuristic)
        name_pattern = r'\b(my name is|i am|i\'m)\s+([A-Za-z\s]{2,50})\b'
        name_match = re.search(name_pattern, user_input.lower())
        if name_match:
            data["name"] = name_match.group(2).strip()
        
        # Extract budget
        budget_pattern = r'\b(\d{3,8})\b'
        budget_match = re.search(budget_pattern, user_input)
        if budget_match:
            data["budget"] = budget_match.group(1)
        
        return data

    async def generate_response_stream(self, user_input: str):
        """
        Generates a streaming response from Groq/Llama for reduced latency.
        
        Yields:
            str: Response chunks as they become available
        """
        if not self._validate_input(user_input):
            yield "I didn't catch that. Could you please repeat?"
            return
        
        try:
            # Add user input to conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Limit conversation history to prevent context bloat
            if len(self.conversation_history) > self.max_history_length:
                # Keep system prompt and last 10 exchanges
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-10:]
            
            # Extract structured data for validation
            extracted_data = self._extract_structured_data(user_input)
            
            # Use faster model for better latency
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Faster model
                messages=self.conversation_history,
                max_tokens=60,
                temperature=0.6,
                top_p=0.9,
                frequency_penalty=0.3,
                presence_penalty=0.3,
                stream=True  # Enable streaming
            )
            
            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
            
            # Sanitize final response
            sanitized_response = self._sanitize_response(full_response)
            
            # Add to conversation history
            self.conversation_history.append({"role": "assistant", "content": sanitized_response})
            
            logger.info(f"Generated streaming response: {sanitized_response[:50]}...")
            
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            yield "I'm experiencing high demand. Please wait a moment and try again."
        except APIError as e:
            logger.error(f"API error: {e}")
            yield "I'm having trouble connecting. Please try again in a moment."
        except InternalServerError as e:
            logger.error(f"Internal server error: {e}")
            yield "I'm experiencing technical difficulties. Please try again shortly."
        except Exception as e:
            logger.error(f"Unexpected error generating response: {e}")
            yield "Sorry, I didn't catch that. Could you please repeat?"

    async def generate_response_cached(self, user_input: str, context: Optional[Dict] = None) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Generates a cached response from Groq/Llama with hallucination prevention.
        
        Returns:
            Tuple[str, Optional[Dict]]: (response_text, extracted_data)
        """
        # Try cache first
        cached_result = response_cache.get(user_input, context)
        if cached_result:
            logger.info(f"Cache hit for: {user_input[:30]}...")
            return cached_result
        
        if not self._validate_input(user_input):
            return "I didn't catch that. Could you please repeat?", None
        
        try:
            # Add user input to conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Limit conversation history to prevent context bloat
            if len(self.conversation_history) > self.max_history_length:
                # Keep system prompt and last 10 exchanges
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-10:]
            
            # Extract structured data for validation
            extracted_data = self._extract_structured_data(user_input)
            
            # Use faster model for better latency
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Faster model
                messages=self.conversation_history,
                max_tokens=60,  # Slightly increased for better context
                temperature=0.6,
                top_p=0.9,
                frequency_penalty=0.3,
                presence_penalty=0.3,
            )
            
            assistant_message = response.choices[0].message.content
            
            # Sanitize response to prevent hallucination
            sanitized_response = self._sanitize_response(assistant_message)
            
            # Add to conversation history
            self.conversation_history.append({"role": "assistant", "content": sanitized_response})
            
            # Cache the response
            response_cache.set(user_input, sanitized_response, extracted_data, context)
            
            logger.info(f"Generated and cached response: {sanitized_response[:50]}...")
            
            return sanitized_response, extracted_data
            
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            return "I'm experiencing high demand. Please wait a moment and try again.", None
        except APIError as e:
            logger.error(f"API error: {e}")
            return "I'm having trouble connecting. Please try again in a moment.", None
        except InternalServerError as e:
            logger.error(f"Internal server error: {e}")
            return "I'm experiencing technical difficulties. Please try again shortly.", None
        except Exception as e:
            logger.error(f"Unexpected error generating response: {e}")
            return "Sorry, I didn't catch that. Could you please repeat?", None

    async def generate_response(self, user_input: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Generates a response from Groq/Llama with hallucination prevention.
        
        Returns:
            Tuple[str, Optional[Dict]]: (response_text, extracted_data)
        """
        if not self._validate_input(user_input):
            return "I didn't catch that. Could you please repeat?", None
        
        try:
            # Add user input to conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Limit conversation history to prevent context bloat
            if len(self.conversation_history) > self.max_history_length:
                # Keep system prompt and last 10 exchanges
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-10:]
            
            # Extract structured data for validation
            extracted_data = self._extract_structured_data(user_input)
            
            # Use faster model for better latency
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Faster model
                messages=self.conversation_history,
                max_tokens=60,  # Slightly increased for better context
                temperature=0.6,
                top_p=0.9,
                frequency_penalty=0.3,
                presence_penalty=0.3,
            )
            
            assistant_message = response.choices[0].message.content
            
            # Sanitize response to prevent hallucination
            sanitized_response = self._sanitize_response(assistant_message)
            
            # Add to conversation history
            self.conversation_history.append({"role": "assistant", "content": sanitized_response})
            
            logger.info(f"Generated response: {sanitized_response[:50]}...")
            
            return sanitized_response, extracted_data
            
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            return "I'm experiencing high demand. Please wait a moment and try again.", None
        except APIError as e:
            logger.error(f"API error: {e}")
            return "I'm having trouble connecting. Please try again in a moment.", None
        except InternalServerError as e:
            logger.error(f"Internal server error: {e}")
            return "I'm experiencing technical difficulties. Please try again shortly.", None
        except Exception as e:
            logger.error(f"Unexpected error generating response: {e}")
            return "Sorry, I didn't catch that. Could you please repeat?", None

    def reset_conversation(self):
        """Reset conversation history for a new call."""
        self.conversation_history = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        logger.info("Conversation history reset")
