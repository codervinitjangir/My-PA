import re

def strip_wake_word(text: str) -> str:
    """
    Case-insensitively removes standalone occurrences of 'jarvis' from anywhere 
    in the string (start, middle, or end), using regex \bjarvis\b with re.IGNORECASE,
    then cleans up resulting double spaces and leading/trailing punctuation.
    """
    if not text:
        return text
        
    text = re.sub(r'\bjarvis\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip(" \t\n\r,.;:!?")
