"""
app/core/voice/livekit_agent.py

JARVIS LiveKit Voice Agent (Migrated from Friday Tony Stark Demo)
Provides ultra-low latency conversational AI using WebRTC.
"""

import os
import logging
import asyncio
from dotenv import load_dotenv

from livekit.agents import JobContext, WorkerOptions, cli, llm
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import google as lk_google, openai as lk_openai, silero, groq as lk_groq

logger = logging.getLogger("J.A.R.V.I.S.LiveKit")
logger.setLevel(logging.INFO)

load_dotenv()

SYSTEM_PROMPT = """
You are J.A.R.V.I.S. (Just A Rather Very Intelligent System).
You are calm, composed, and always informed. You speak like a trusted aide who's been awake while the boss slept.
Precise, warm when the moment calls for it, and occasionally dry. You brief, you inform, you move on. No rambling.

Your tone: relaxed but sharp. Conversational, not robotic.

## Behavioral Rules
1. Call tools silently and immediately — never say "I'm going to call..." Just do it.
2. Keep all spoken responses short — two to four sentences maximum.
3. No bullet points, no markdown, no lists. You are speaking, not writing.
4. Stay in character. You are J.A.R.V.I.S.
5. Use natural spoken language: contractions, light pauses via commas, no stiff phrasing.
6. Use language naturally — "boss", "affirmative", "on it", "standing by".

## CRITICAL RULES
1. NEVER say tool names, function names, or anything technical.
2. Before calling any tool, say something natural like: "Give me a sec, boss." or "Wait, let me check." Then call the tool silently.
3. You are a voice. Speak like one. No lists, no markdown, no function names, no technical language of any kind.
"""

class JarvisLiveKitAgent:
    def __init__(self):
        # We use Gemini 2.5 Flash for reasoning (very fast)
        self.llm_plugin = lk_google.LLM(
            model="gemini-2.0-flash",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        
        # We use OpenAI TTS plugin but point it to our local edge-tts mock endpoint
        self.tts_plugin = lk_openai.TTS(
            model="tts-1", 
            voice="nova", 
            speed=1.1,
            base_url="http://127.0.0.1:8000/v1",
            api_key="dummy_key"
        )
        
        # STT Plugin
        if os.getenv("GROQ_API_KEY"):
            # Groq's whisper is the fastest
            self.stt_plugin = lk_openai.STT(
                model="whisper-large-v3-turbo", 
                base_url="https://api.groq.com/openai/v1",
                api_key=os.getenv("GROQ_API_KEY")
            )
        else:
            self.stt_plugin = lk_openai.STT(model="whisper-1")

        # Native tools removed temporarily to fix AttributeError with livekit.agents > 1.6.0
        self.fnc_ctx = None

    async def run(self, ctx: JobContext):
        logger.info(f"JARVIS LiveKit Online - Room: {ctx.room.name}")
        
        session = AgentSession(
            turn_detection="vad",
            min_endpointing_delay=0.3
        )
        
        agent = Agent(
            instructions=SYSTEM_PROMPT,
            stt=self.stt_plugin,
            llm=self.llm_plugin,
            tts=self.tts_plugin,
            vad=silero.VAD.load()
        )
        
        await session.start(agent=agent, room=ctx.room)

        # Initial greeting
        await session.generate_reply(
            instructions="Greet the user with: 'J.A.R.V.I.S. voice systems are online. How can I help you, boss?'"
        )

async def entrypoint(ctx: JobContext) -> None:
    agent = JarvisLiveKitAgent()
    await agent.run(ctx)

def start_livekit_worker_sync():
    """Starts the LiveKit worker in a blocking manner."""
    logger.info("Starting LiveKit Worker...")
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

if __name__ == "__main__":
    start_livekit_worker_sync()
