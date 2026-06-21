"""
Backward compatibility stub for existing code referencing GroqService.
"""
from app.providers.groq_provider import GroqProvider as GroqService
from app.providers.groq_provider import AllGroqApisFailedError, escape_curly_braces
