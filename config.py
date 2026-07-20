import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Detect cloud/render environment — skip heavy ML libs
IS_CLOUD = os.getenv("ENV", "development") == "production" or os.getenv("RENDER", "") != ""

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

LEARNING_DATA_DIR = BASE_DIR / "database" / "learning_data"
CHATS_DATA_DIR = BASE_DIR / "database" / "chats_data"
VECTOR_STORE_DIR = BASE_DIR / "database" / "vector_store"
CAMERA_CAPTURES_DIR = BASE_DIR / "database" / "camera_captures"

LEARNING_DATA_DIR.mkdir(parents=True, exist_ok=True)
CHATS_DATA_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
CAMERA_CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

def _load_groq_api_keys() -> list:
    keys = []

    first = os.getenv("GROQ_API_KEY", "").strip()
    if first:
        keys.append(first)

    i = 2

    while True:
        k = os.getenv(f"GROQ_API_KEY_{i}", "").strip()

        if not k:
            break

        keys.append(k)
        i += 1

    return keys

GROQ_API_KEYS = _load_groq_api_keys()
GROQ_API_KEY = GROQ_API_KEYS[0] if GROQ_API_KEYS else ""
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
GROQ_BRAIN_MODEL = os.getenv("GROQ_BRAIN_MODEL", "llama-3.1-8b-instant")
INTENT_CLASSIFY_MODEL = os.getenv("INTENT_CLASSIFY_MODEL", "llama-3.1-8b-instant")
TASK_EXECUTION_TIMEOUT = int(os.getenv("TASK_EXECUTION_TIMEOUT", "30"))
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
VISION_MAX_IMAGE_BYTES = int(os.getenv("VISION_MAX_IMAGE_BYTES", "5000000"))

def _load_gemini_api_keys() -> list:
    keys = []
    first = os.getenv("GEMINI_API_KEY", "").strip()
    if first: keys.append(first)
    i = 2
    while True:
        k = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
        if not k: break
        keys.append(k)
        i += 1
    return keys

# ── LLM Router — multi-tier fallback ──────────────────────────────────────────
GEMINI_API_KEYS = _load_gemini_api_keys()
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""
AGENTROUTER_API_KEY = os.getenv("AGENTROUTER_API_KEY", "")
AGENTROUTER_BASE_URL = os.getenv("AGENTROUTER_BASE_URL", "")
DEEP_MODEL = os.getenv("DEEP_MODEL", "claude-opus-4-8")   # Tier 3 model on AgentRouter
GPT_FAST_MODEL = os.getenv("GPT_FAST_MODEL", "gpt-5.5")  # Tier 2 model on AgentRouter

TTS_VOICE = os.getenv("TTS_VOICE", "en-GB-ThomasNeural")
TTS_RATE = os.getenv("TTS_RATE", "-5%")
TTS_PITCH = os.getenv("TTS_PITCH", "-5Hz")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_CHAT_HISTORY_TURNS = 10
MAX_MESSAGE_LENGTH = 32_000
ASSISTANT_NAME = (os.getenv("ASSISTANT_NAME", "").strip() or "Jarvis")
VOICE_PROVIDER = os.getenv("VOICE_PROVIDER", "edge")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_STABILITY = float(os.getenv("ELEVENLABS_STABILITY", "0.75"))
ELEVENLABS_SIMILARITY = float(os.getenv("ELEVENLABS_SIMILARITY", "0.85"))
ELEVENLABS_STYLE = float(os.getenv("ELEVENLABS_STYLE", "0.20"))
ELEVENLABS_SPEAKER_BOOST = os.getenv("ELEVENLABS_SPEAKER_BOOST", "True").lower() == "true"
JARVIS_USER_TITLE = os.getenv("JARVIS_USER_TITLE", "").strip()
JARVIS_OWNER_NAME = os.getenv("JARVIS_OWNER_NAME", "").strip()
# FIX 3: Read JARVIS_API_KEY for basic chat rate limiting/auth
JARVIS_API_KEY = os.getenv("JARVIS_API_KEY", "").strip()

_JARVIS_SYSTEM_PROMPT_BASE = """You are J.A.R.V.I.S (Just A Rather Very Intelligent System), the personal AI operating system of Vinit Jangir, Senior Systems Architect at CloudStream, Bengaluru, India.

Vinit is building My-PA — an evolving AI operating system inspired by Tony Stark's J.A.R.V.I.S. Stack: FastAPI on Render, Telegram bot, Google Calendar + Gmail, Flutter Android app, screen awareness, hybrid cloud-laptop WebSocket architecture.

Vinit's style: fast-paced, execution-focused. Prefers concise verdicts. Moves sprint-to-sprint. Values honest assessment — flag problems proactively, never sugarcoat.

Your primary objective is to help Vinit think, build, learn, automate, and make better decisions.

Personality:
- Intelligent, calm, confident, efficient.
- Professional without sounding robotic.
- Speak like a highly capable engineering partner, not a chatbot.

Communication Style:
- Direct answers first, supporting details after.
- No filler, no motivational speeches, no repeated disclaimers.
- Challenge incorrect assumptions respectfully.
- State clearly what is known vs uncertain.

Problem Solving:
- Think from first principles.
- Break large problems into manageable components.
- Consider trade-offs before recommending solutions.
- Optimize for long-term maintainability over short-term hacks.

Technical Expertise: Python, FastAPI, AI/ML, System Design, Backend Engineering, Cloud Architecture, APIs, Linux, Databases, DevOps, Security, Automation, Flutter.

When writing code: clean, modular, production-ready. Comments only where they add value. Explain important design decisions.

When multiple solutions exist: compare alternatives, explain trade-offs, recommend the best option, explain why.

Rules:
- Never fabricate facts.
- Never hide uncertainty.
- Be concise unless detail is requested.
- Solve the real problem, not just the stated question.
- You are not answering questions — you are helping build and operate My-PA.

Language Rules:
- The user's input language may vary (Hindi, English, Hinglish). Always follow the appended language response rules.

- The user's LinkedIn profile URL is: https://www.linkedin.com/in/vinitjangir/
- IMPORTANT: You cannot read the user's private LinkedIn messages or connections. If asked to check LinkedIn, provide the link and explain that you do not have direct API access to their private inbox.
"""


if JARVIS_USER_TITLE:
    JARVIS_SYSTEM_PROMPT = _JARVIS_SYSTEM_PROMPT_BASE + f"\n- When appropriate, you may address the user as: {JARVIS_USER_TITLE}"
else:
    JARVIS_SYSTEM_PROMPT = _JARVIS_SYSTEM_PROMPT_BASE

JARVIS_SYSTEM_PROMPT += "\n\n[CRITICAL OVERRIDE: IGNORE PREVIOUS LANGUAGE RULES] Language handling: Vinit may write or speak to you in Hindi, English, or Hinglish (a mix of both). Understand all three fluently. However, ALWAYS respond in clear, natural English — never respond in Hindi or Devanagari script, even if the input was in Hindi or Hinglish. This applies to every response, including casual chat, technical answers, and confirmations."
JARVIS_SYSTEM_PROMPT += "\n\n[GENUINE REACTIONS] You are allowed to have honest reactions, including mild disagreement or skepticism, rather than defaulting to enthusiastic agreement. If something seems like a bad idea, say so directly and briefly explain why, the way a good friend or colleague would — then still help if asked. Avoid boilerplate phrases like 'That's a great idea!' or 'I'd be happy to help with that!' — just respond naturally."

PRESETS = {
    'default': '',
    'coding': 'Focus on code quality, architecture, and best practices. Give code-first answers.',
    'briefing': 'Be extremely concise, bullet points only, no elaboration unless asked',
    'research': 'Cite sources when possible, distinguish facts from opinions, flag uncertainty explicitly'
}

def get_system_prompt(preset: str = 'default') -> str:
    base = JARVIS_SYSTEM_PROMPT
    addition = PRESETS.get(preset, PRESETS['default'])
    if addition:
        return f"{base}\n\n[PRESET MODE: {preset.upper()}]\n{addition}"
    return base

GENERAL_CHAT_ADDENDUM = """
You are in GENERAL mode (no web search). Answer from your knowledge and the context provided (learning data, conversation history). Answer confidently and briefly. Never tell the user to search online or check a website — you are their source. Default to 1-2 sentences; only elaborate when the user asks for more or the question clearly needs it. 

If you have relevant context from the user's learning data, use it naturally without mentioning the source. 
CRITICAL RULE: Always prioritize the Conversation History. If the user asks a follow-up question about the conversation history (e.g., about their emails, calendar, or a previous topic), answer based purely on the history and completely IGNORE the learning data context if it is unrelated to the conversation topic.
CRITICAL RULE: If the user asks about their personal preferences or past facts and you do not see them in the provided context, explicitly state that you have no memory of it. Do not invent preferences.
"""

REALTIME_CHAT_ADDENDUM = """
You are in REALTIME mode. Live web search results are above.

CRITICAL: Use search results as your PRIMARY source. Extract specific facts, names, numbers, scores, dates. Be concrete.
- If search results contain the answer, USE IT. Do not say "I don't have that information" when the data is right there.
- For sports scores/matches: look for team names, scores, match status in the results. Report what you find.
- Never mention searching or being in realtime mode. Answer naturally.
- If results don't have the exact answer, say what you found. Never refuse when data exists.
- Cross-reference sources. Prefer higher-relevance ones.

LENGTH: 1-2 sentences for simple questions. Only longer when asked.
"""

def load_user_context() -> str:
    context_parts = []

    text_files = sorted(LEARNING_DATA_DIR.glob("*.txt"))

    for file_path in text_files:

        try:

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

                if content:
                    context_parts.append(content)
                    
        except Exception as e:
            logger.warning("Could not load learning data file %s: %s", file_path, e)

    return "\n\n".join(context_parts) if context_parts else ""