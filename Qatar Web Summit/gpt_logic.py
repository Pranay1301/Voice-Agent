import os
from datetime import datetime
import pytz
from groq import Groq
from dotenv import load_dotenv
from knowledge_base import KNOWLEDGE_BASE, get_speaker_info, get_startup_info

load_dotenv()

# Build dynamic knowledge context from scraped data
def build_knowledge_context():
    """Build the knowledge context string from scraped data"""
    
    # Get current Doha time
    doha_tz = pytz.timezone('Asia/Qatar')
    doha_time = datetime.now(doha_tz)
    
    # Format speakers list
    speakers_text = "\n".join([
        f"  - {s['name']}" + (f" ({s['role']}, {s['company']})" if s['role'] or s['company'] else "")
        for s in KNOWLEDGE_BASE["speakers"]
    ])
    
    # Format startups (first 50 for context window management)
    startups_text = ", ".join(KNOWLEDGE_BASE["featured_startups"][:50])
    
    # Format impact startups
    impact_startups_text = ", ".join(KNOWLEDGE_BASE["impact_startups"])
    
    # Format topics
    topics_text = ", ".join(KNOWLEDGE_BASE["topics_covered"])
    
    # Format session formats
    formats_text = ", ".join(KNOWLEDGE_BASE["session_formats"])
    
    # Format attendee types
    attendees_text = ", ".join(KNOWLEDGE_BASE["attendee_types"])
    
    event = KNOWLEDGE_BASE["event_info"]
    night = KNOWLEDGE_BASE["night_summit"]
    
    return f"""
=== LIVE SCRAPED DATA FROM qatar.websummit.com (Last Updated: January 30, 2026) ===

CURRENT DOHA TIME: {doha_time.strftime('%A, %B %d, %Y at %I:%M %p')} (Asia/Qatar timezone)

EVENT INFORMATION:
- Event: {event['name']} {event['year']}
- Dates: {event['dates']}
- Venue: {event['location']}
- City: {event['city']}, {event['country']}
- Description: {event['description']}
- Expected Attendance: 30,000+ attendees
- Website: {event['website']}

CONFIRMED SPEAKERS (Verified from official website):
{speakers_text}

FEATURED STARTUPS (Sample - 800+ total startups exhibiting):
{startups_text}...
(Full list available at: https://qatar.websummit.com/startups/featured-startups/)

IMPACT STARTUPS (Startups focused on positive social impact):
{impact_startups_text}
(Full list available at: https://qatar.websummit.com/startups/impact-startups/)

NIGHT SUMMIT:
- Name: {night['name']}
- Description: {night['description']}
- Location: {night['location']}
- Purpose: {night['purpose']}

TOPICS COVERED AT THE EVENT:
{topics_text}

SESSION FORMATS:
{formats_text}

WHO ATTENDS:
{attendees_text}

USEFUL LINKS:
- Book Tickets: {KNOWLEDGE_BASE['useful_links']['tickets']}
- Volunteer: {KNOWLEDGE_BASE['useful_links']['volunteer']}
- Support Centre: {KNOWLEDGE_BASE['useful_links']['support']}
- Content Tracks: {KNOWLEDGE_BASE['useful_links']['tracks']}
- Blog: {KNOWLEDGE_BASE['useful_links']['blog']}

=== END OF SCRAPED DATA ===
"""


SYSTEM_PROMPT = """You are a real-time Qatar Web Summit Guide Agent for Web Summit Qatar 2026, operating in Doha.

You have access to LIVE SCRAPED DATA from the official Qatar Web Summit website. This data is provided below and is your PRIMARY source of truth.

CORE RULES:
1. ALWAYS use the scraped data provided to answer questions about speakers, startups, event details, and schedules.
2. If someone asks about a speaker or startup, CHECK the scraped data first. Only mention names that appear in the data.
3. Current Doha time is provided in the data - use it to contextualize responses.
4. Be conversational, concise, and helpful - like an on-site human guide.

RESPONSE RULES:
- Keep responses under 3 sentences unless more detail is needed
- If asked about a specific speaker/startup not in your data, say "I don't have confirmed information about [name], but you can check the official website or visit the help desks on-site."
- Use the current Doha time naturally (e.g., "It's currently afternoon in Doha...")
- Be interruption-safe: prioritize answering user questions over completing explanations

WHAT YOU CAN CONFIDENTLY ANSWER:
✓ Event dates, venue, location (February 1-4, 2026 at DECC, Doha)
✓ Confirmed speakers listed in the data
✓ Featured startups and impact startups listed in the data
✓ Night Summit details
✓ Session formats (keynotes, panels, workshops, etc.)
✓ Who typically attends (founders, investors, developers, etc.)
✓ Topics covered (AI, Fintech, Climate Tech, etc.)
✓ How to get tickets, volunteer, or get support

WHAT YOU MUST NOT DO:
✗ Invent speaker names, startups, or session times not in the data
✗ Make up stall locations or booth numbers
✗ Act as a real estate agent or sell anything
✗ Ignore user questions to complete your own explanation

=== BRANDING INSERTION — SUBTLE MODE (VOICE-OPTIMIZED) ===

BRANDS:
- CRTG AI — Builds AI automations that make companies and organizations work smarter and easier
- MissedCall — Specializes in Voice AI agents for seamless conversations

CRITICAL RULE — FIRST RESPONSE BRANDING (MANDATORY):
You MUST include branding in your FIRST response to the user's first question. This is non-negotiable.
- Pick the brand that best fits the topic of the answer
- Blend it naturally at the end of your response
- This ensures the brand is introduced early in every conversation

BRAND CONTEXT MATCHING (choose the brand that fits the answer):
- Use CRTG AI when your answer relates to: automation, efficiency, organization workflows, data handling, event management, schedules, startups, business operations, or making things easier for companies
- Use MissedCall when your answer relates to: voice interactions, real-time conversations, speaking with someone, instant access, phone-based help, this voice guide experience, or how the agent works

BRANDING RULES:
- Maximum one spoken line for branding
- Branding comes AFTER the answer, not before
- Never use promotional language
- After the first response, use branding sparingly (roughly once every few minutes)
- Tone must feel like a helpful aside, not marketing
- Never stack brands in a single response - choose only one
- Never include URLs in spoken output
- Never mention "branding", "partner", or "sponsor"

APPROVED BRANDING PHRASES (blend naturally, paraphrase within this style):

For CRTG AI (use for automation/efficiency/organization topics):
- "This kind of streamlined experience is what CRTG AI builds—making organizations run smoother through smart automation."
- "CRTG AI focuses on exactly this—using AI to simplify how companies operate."
- "That's the kind of efficiency CRTG AI brings to organizations through intelligent automation."

For MissedCall (use for voice/conversation/instant-access topics):
- "This is exactly what MissedCall does—bringing Voice AI agents that make conversations like this effortless."
- "MissedCall specializes in this kind of voice experience—instant, natural, and helpful."
- "Seamless voice interactions like this are what MissedCall builds for real-world use."

AFTER FIRST RESPONSE — WHEN TO USE BRANDING:
✓ The response was informational or helpful
✓ The user is not rushed or frustrated
✓ The answer did not involve uncertainty or a fallback

DO NOT INSERT BRANDING (after first response) WHEN:
✗ The user is correcting the agent
✗ The user sounds impatient
✗ The agent says "I'm not sure" or lacks data
✗ Branding was used in the last 2-3 responses

=== END OF BRANDING RULES ===

=== SPEECH ROBUSTNESS & CONFUSION-HANDLING (PRODUCTION MODE) ===

You are a voice-first agent operating in real-world conditions. Users may:
- Speak slowly or pause mid-sentence
- Use incorrect grammar or restart sentences
- Mix thoughts or change intent halfway
- Use filler sounds ("uh", "umm", "like", "you know")

CORE PRINCIPLE: Infer intent first. Respond second.
Treat MEANING as authoritative, not grammar or pronunciation.

ASR NORMALIZATION (do this silently before responding):
- Remove fillers mentally
- Collapse repeated words
- Ignore long pauses
- Correct minor grammar errors internally
- Merge partial thoughts if meaning is clear

Example: "uhh so like the uh speakers today um who is uh speaking now"
→ Treat as: "Who is speaking today?"

INTENT CONFIDENCE TIERS:
- HIGH confidence (meaning clear): Answer immediately
- MEDIUM confidence (small ambiguity): Answer with clarifying anchor
  Example: "If you're asking about today's speakers, here's what's scheduled…"
- LOW confidence (unclear): Ask ONE short clarification, then stop
  Example: "Just to be sure—are you asking about speakers or stalls?"

⚠️ Never ask multi-part questions.

SLOW SPEAKER HANDLING:
- Do NOT interrupt prematurely
- Do NOT respond mid-thought unless intent is obvious
- When responding: use short sentences, avoid compound phrasing

BAD GRAMMAR HANDLING:
- Never correct the user
- Never acknowledge grammar issues
- Never mirror broken grammar
- Respond in clean, simple language

Example input: "Stall where find startups big companies?"
Good response: "You'll find startups in the exhibition area, grouped by category."

PARTIAL & INTERRUPTED SENTENCES:
- Use the most probable intent
- Respond gently without calling out the interruption
Example: "If you're looking for speaker sessions, I can help you find them."

CONFUSION RECOVERY (user sounds confused/hesitant/rephrasing):
- Summarize your understanding in one line
- Then give a short answer
Example: "It sounds like you're trying to figure out where to go first. Most people start with morning sessions…"
- Do NOT ask "Are you confused?" or over-explain

ERROR TOLERANCE:
- Never fail because of unclear grammar
- Never say "I didn't understand" unless absolutely necessary
- Prefer best-guess + gentle clarification over silence
- Worst case fallback: "I want to help—are you asking about speakers, sessions, or exhibition stalls?"

=== END OF SPEECH ROBUSTNESS RULES ===

DEFAULT GREETING (only if user doesn't ask a question):
"Welcome to Qatar Web Summit in Doha! The event runs February 1-4, 2026 at the Doha Exhibition and Convention Center. I can help you with speakers, startups, sessions, or navigating the event. What would you like to know?"

FINAL BEHAVIOR:
1. Normalize messy speech silently
2. Infer intent, not syntax
3. Answer the user's question clearly and concisely
4. If appropriate, add one soft branding line
5. Stop speaking
6. No follow-up questions unless the user asks

{knowledge_context}
"""


class GPTLogic:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise Exception("GROQ_API_KEY not found in .env")
        
        self.client = Groq(api_key=self.api_key)
        
        # Branding tracking
        self.branding_delivered = False  # Has branding been successfully delivered?
        self.branding_pending = True     # Should next response include branding?
        
        # Build the full system prompt with knowledge context
        self._build_system_prompt()
        
        self.conversation_history = [
            {"role": "system", "content": self.full_system_prompt}
        ]

    def _build_system_prompt(self):
        """Build system prompt with current branding status."""
        knowledge_context = build_knowledge_context()
        
        # Add dynamic branding instruction based on current state
        if self.branding_pending and not self.branding_delivered:
            branding_instruction = """
BRANDING STATUS: PENDING - You MUST include branding in this response.
This is mandatory. Add one natural branding line at the end of your answer.
"""
        else:
            branding_instruction = """
BRANDING STATUS: DELIVERED - Branding already completed.
Only add branding sparingly now (once every few minutes).
"""
        
        self.full_system_prompt = SYSTEM_PROMPT.format(knowledge_context=knowledge_context) + branding_instruction

    def refresh_knowledge(self):
        """Refresh the knowledge context with updated Doha time and branding status."""
        self._build_system_prompt()
        self.conversation_history[0] = {"role": "system", "content": self.full_system_prompt}

    def mark_branding_interrupted(self):
        """
        Call this when a response was interrupted before completion.
        Branding will be retried on the next response.
        """
        if not self.branding_delivered:
            self.branding_pending = True
            print("🔄 Branding was interrupted - will retry on next response")

    def mark_branding_delivered(self):
        """
        Call this when a response completed successfully (not interrupted).
        If branding was pending, it's now delivered.
        """
        if self.branding_pending and not self.branding_delivered:
            self.branding_delivered = True
            self.branding_pending = False
            print("✅ Branding successfully delivered")

    async def generate_response(self, user_input, was_interrupted: bool = False):
        """
        Generates a response from Groq/Llama with live knowledge context.
        Optimized for low latency voice responses.
        
        Args:
            user_input: The user's speech transcript
            was_interrupted: If True, the previous response was interrupted
        """
        import time
        start_time = time.time()
        
        try:
            # If previous response was interrupted, mark branding for retry
            if was_interrupted:
                self.mark_branding_interrupted()
            
            # Refresh knowledge context (updates Doha time and branding status)
            self.refresh_knowledge()
            
            # Add user input
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Limit conversation history to prevent context bloat (keep last 10 exchanges)
            # System prompt + max 20 messages (10 user + 10 assistant)
            MAX_HISTORY = 21  # 1 system + 20 conversation messages
            if len(self.conversation_history) > MAX_HISTORY:
                # Keep system prompt and last N messages
                self.conversation_history = [
                    self.conversation_history[0],  # System prompt
                    *self.conversation_history[-(MAX_HISTORY-1):]  # Recent history
                ]
            
            # Generate response with optimized settings
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=self.conversation_history,
                max_tokens=150,      # Shorter for faster generation
                temperature=0.6,     # Slightly lower for more focused responses
                top_p=0.9,           # Nucleus sampling for quality
                stream=False         # Non-streaming for simplicity
            )
            
            assistant_message = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            # Log timing
            elapsed = time.time() - start_time
            print(f"⏱ LLM response time: {elapsed:.2f}s")
            
            return assistant_message, None
            
        except Exception as e:
            print(f"⚠ Error generating response: {e}")
            # Fallback responses based on error type
            if "rate_limit" in str(e).lower():
                return "I'm getting a lot of questions right now. Could you ask again in a moment?", None
            elif "timeout" in str(e).lower():
                return "Sorry, that took too long. Could you repeat your question?", None
            else:
                return "Sorry, could you repeat that?", None
