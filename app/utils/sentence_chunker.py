"""
app/utils/sentence_chunker.py — Sentence & Clause Boundary Buffer for TTS Streaming

Buffers raw LLM token streams into natural sentence/clause boundaries.
Prevents single-token fragmented TTS requests while enabling ultra-low TTFA (~200ms after sentence 1).
"""

import re
import logging
from typing import AsyncIterator, List

logger = logging.getLogger("J.A.R.V.I.S")

# Common abbreviations that shouldn't trigger a sentence boundary
ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "vs", "st", "ave", "rd",
    "approx", "dept", "est", "min", "sec", "max", "vol", "no", "etc", "e.g", "i.e"
}

class SentenceChunker:
    """
    Buffers token stream and yields complete sentences or natural clause units.
    """
    
    def __init__(self, min_clause_words: int = 3, max_clause_words: int = 25):
        self.min_clause_words = min_clause_words
        self.max_clause_words = max_clause_words
        self.buffer = ""
        self.sentences_yielded = 0


    def clean_text_for_tts(self, text: str) -> str:
        """Strip URLs, code snippets, and markdown symbols for clean TTS reading."""
        # Strip code blocks
        text = re.sub(r'```[\s\S]*?```', ' code block ', text)
        # Strip inline code
        text = re.sub(r'`[^`]+`', '', text)
        # Replace URLs with "link"
        text = re.sub(r'https?://\S+', 'a link', text)
        # Remove bold/italic markdown formatting
        text = re.sub(r'\*\*?(.*?)\*\*?', r'\1', text)
        # Remove bullet points
        text = re.sub(r'^\s*[-•*]\s+', '', text, flags=re.MULTILINE)
        # Clean extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def is_sentence_boundary(self, text: str) -> bool:
        """Check if buffer ends with a true sentence boundary."""
        trimmed = text.rstrip()
        if not trimmed:
            return False
            
        last_char = trimmed[-1]
        if last_char not in ('.', '!', '?', '\n'):
            return False
            
        # Check if the word before '.' is a known abbreviation
        words = trimmed.split()
        if len(words) > 0:
            last_word = words[-1].rstrip('.!?').lower()
            if last_word in ABBREVIATIONS:
                return False
                
        # Check decimal numbers (e.g., 3.14)
        if re.search(r'\d\.\d$', trimmed):
            return False
            
        return True

    def process_token(self, token: str) -> List[str]:
        """
        Process a single incoming LLM token.
        Returns a list of complete sentence strings ready for TTS (if any).
        """
        self.buffer += token
        ready_sentences = []

        # Check for paragraph breaks or standard sentence endings
        if '\n\n' in self.buffer or self.is_sentence_boundary(self.buffer):
            words = self.buffer.split()
            if len(words) >= 2:  # Min 2 words to synthesize
                cleaned = self.clean_text_for_tts(self.buffer)
                if cleaned:
                    ready_sentences.append(cleaned)
                    self.sentences_yielded += 1
                self.buffer = ""

        # Clause boundary fallback for very long sentences (commas, colons, dashes)
        elif any(punct in self.buffer for punct in (',', ';', ':', '—')):
            words = self.buffer.split()
            if len(words) >= self.min_clause_words:
                # Find last clause punctuation index
                split_match = re.search(r'([,;:—])\s+', self.buffer)
                if split_match:
                    split_idx = split_match.end()
                    clause = self.buffer[:split_idx]
                    self.buffer = self.buffer[split_idx:]
                    cleaned = self.clean_text_for_tts(clause)
                    if cleaned:
                        ready_sentences.append(cleaned)
                        self.sentences_yielded += 1

        # Safety flush if buffer exceeds max words without punctuation
        elif len(self.buffer.split()) >= self.max_clause_words:
            cleaned = self.clean_text_for_tts(self.buffer)
            if cleaned:
                ready_sentences.append(cleaned)
                self.sentences_yielded += 1
            self.buffer = ""

        return ready_sentences

    def flush(self) -> List[str]:
        """Flush remaining buffer at the end of the LLM stream."""
        remaining = []
        if self.buffer.strip():
            cleaned = self.clean_text_for_tts(self.buffer)
            if cleaned and len(cleaned) > 1:
                remaining.append(cleaned)
                self.sentences_yielded += 1
        self.buffer = ""
        return remaining


async def stream_sentences(token_generator: AsyncIterator[str]) -> AsyncIterator[str]:
    """Helper async generator that wraps an async token stream and yields sentences."""
    chunker = SentenceChunker()
    async for token in token_generator:
        sentences = chunker.process_token(token)
        for sentence in sentences:
            yield sentence
            
    for remaining_sentence in chunker.flush():
        yield remaining_sentence
