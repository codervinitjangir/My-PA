import re
import logging

logger = logging.getLogger("J.A.R.V.I.S.Redact")

# Compile patterns for performance. Order matters! Specific wins over generic.
REDACT_RULES = [
    # 1. Cloud & API Keys
    (re.compile(r'AKIA[0-9A-Z]{16}'), '[REDACTED_AWS_KEY]'),
    (re.compile(r'(?:sk|pk|rk)_(?:test|live)_[0-9a-zA-Z]{24}'), '[REDACTED_STRIPE_KEY]'),
    (re.compile(r'gh[pousr]_[0-9a-zA-Z]{36}'), '[REDACTED_GH_TOKEN]'),
    (re.compile(r'sk-[a-zA-Z0-9]{48}'), '[REDACTED_OPENAI_KEY]'),
    (re.compile(r'AIza[0-9A-Za-z-_]{35}'), '[REDACTED_GOOG_KEY]'),
    
    # 2. Authorization Headers & JWTs
    (re.compile(r'(?i)(?:Bearer|Basic)\s+[a-zA-Z0-9=_\-\.]+'), '[REDACTED_AUTH_HEADER]'),
    (re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'), '[REDACTED_JWT]'),
    
    # 3. Keyword-anchored credentials
    (re.compile(r'(?i)\b(?:password|secret|token|apikey)\b\s*[:=]\s*(\S+)'), r'[REDACTED_CREDENTIAL]'),
    
    # 4. Generic Hex strings (usually hashes, salts, or generic keys)
    (re.compile(r'\b[0-9a-fA-F]{32,}\b'), '[REDACTED_HEX]'),
    
    # 5. PII (Emails, Cards, OTPs)
    (re.compile(r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'), '[REDACTED_EMAIL]'),
    (re.compile(r'\b\d(?:[ -]*\d){12,18}\b'), '[REDACTED_CARD]'), # 13-19 digit cards
    
    # 6. OTPs (near keywords)
    (re.compile(r'(?i)(\b(?:otp|2fa|code|pin)\b.{0,20}?)\b\d{4,8}\b'), r'\g<1>[REDACTED_OTP]'),
    (re.compile(r'(?i)\b\d{4,8}\b(.{0,20}?\b(?:otp|2fa|code|pin)\b)'), r'[REDACTED_OTP]\g<1>'),
]

def redact_text(text: str) -> str:
    """
    Scrub sensitive data from text before it is logged or stored.
    Rules are applied in sequence.
    """
    if not text:
        return text
        
    original_text = text
    for pattern, replacement in REDACT_RULES:
        text = pattern.sub(replacement, text)
        
    if text != original_text:
        logger.warning('[MEMORY] Redacted sensitive content before storage')
        
    return text
