"""
app/utils/phonetic_normalizer.py — Tech Acronym Phonetic Normalizer for Natural Voice UX

Transforms developer acronyms, technical terms, and CLI syntax into natural spoken phonetic text
prior to TTS synthesis, eliminating robotic mispronunciation.
"""

import re
from typing import Dict

# Dictionary mapping technical acronyms to natural spoken phonetics
TECH_ACRONYM_MAP: Dict[str, str] = {
    r"\bVS Code\b": "Visual Studio Code",
    r"\bvscode\b": "Visual Studio Code",
    r"\bJSON\b": "JAY-sahn",
    r"\bjson\b": "JAY-sahn",
    r"\bPyAutoGUI\b": "Pie Auto G U I",
    r"\bpyautogui\b": "Pie Auto G U I",
    r"\bCLI\b": "command line interface",
    r"\bAPI\b": "A P I",
    r"\bAPIs\b": "A P Is",
    r"\bGUI\b": "gooey",
    r"\bSQL\b": "sequel",
    r"\bMySQL\b": "My Sequel",
    r"\bPostgreSQL\b": "Postgres Sequel",
    r"\bHTTPS?\b": "H T T P S",
    r"\bURL\b": "U R L",
    r"\bURLs\b": "U R Ls",
    r"\bRAM\b": "ram",
    r"\bCPU\b": "C P U",
    r"\bCPUs\b": "C P Us",
    r"\bOS\b": "O S",
    r"\bLLM\b": "L L M",
    r"\bLLMs\b": "L L Ms",
    r"\bSTT\b": "S T T",
    r"\bTTS\b": "T T S",
    r"\bVAD\b": "vadd",
    r"\bUI\b": "U I",
    r"\bUX\b": "U X",
    r"\bSDK\b": "S D K",
    r"\bSDKs\b": "S D Ks",
    r"\bWAF\b": "waff",
    r"\bYAML\b": "yam-mul",
    r"\bHTML\b": "H T M L",
    r"\bCSS\b": "C S S",
    r"\bJWT\b": "J W T",
    r"\bOAuth\b": "O Auth"
}

class PhoneticNormalizer:
    """
    Normalizes input text for natural speech synthesis.
    """
    @staticmethod
    def normalize_for_tts(text: str) -> str:
        if not text or not isinstance(text, str):
            return ""

        result = text
        for pattern, replacement in TECH_ACRONYM_MAP.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        return result
