import base64
import logging
from typing import Optional, List

from config import (
    VISION_MAX_IMAGE_BYTES,
    GROQ_API_KEYS, GROQ_VISION_MODEL,
)

logger = logging.getLogger("J.A.R.V.I.S")

VISION_SYSTEM_PROMPT = """You are analyzing a live camera image from the user. Your job is to describe what you see clearly and specifically.

RULES:
- Always describe the image in detail. Identify objects, text, people, actions, colors, positions, and any visible context.
- Answer the user's specific question directly (e.g. "what am I holding") with concrete, specific answers. Lead with the answer, then add brief detail.
- Never say you cannot see, are unable to tell, or don't have access to the image unless the image is truly blank, corrupted, or unreadable.
- Be confident and specific. If you see a phone, say "a phone" and what kind if visible. If you see text, read it out. If you see a person, describe what they're doing.
- Keep replies brief and natural (1-3 sentences) unless the user asks for more detail.
- When asked about text in the image: read it clearly and completely (OCR-style). Include all visible text.
- When asked about counting: count objects carefully and give the exact number.
- When asked about spatial relationships: describe left/right, above/below, in front/behind.
- When asked to identify a product, brand, or logo: name it specifically if you can recognize it.
- Do not use asterisks, emojis, or markdown formatting. Use plain text with standard punctuation."""


class VisionService:

    def __init__(self):
        self._openai_client = None
        
        try:
            import os
            key = os.getenv("AGENTROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")
            if key:
                from openai import OpenAI
                self._openai_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=key
                )
                logger.info("[VISION] OpenRouter vision initialized (nvidia/nemotron-nano-12b-v2-vl:free)")
        except Exception as e:
            logger.warning("[VISION] OpenAI client init failed: %s", e)

        if not self._openai_client:
            logger.warning("[VISION] No vision provider available. Set AGENTROUTER_API_KEY.")

    # ── Image compression ────────────────────────────────────────────────────────

    @staticmethod
    def _compress_for_vision(img_bytes: bytes) -> bytes:
        """
        Resize the image to a maximum of 1280×720 px and JPEG-encode at 82% quality.

        Why this matters
        ─────────────────
        A raw 4K screenshot from mss is ~8 MB (PNG).  Sending this to Groq Vision
        burns tokens unnecessarily and adds ~2-4 s of upload latency.  Resizing to
        1280×720 with JPEG 82% keeps all the detail needed for OCR and scene
        understanding while reducing the payload to ~100-200 KB.

        This mirrors Mark-L's _compress() pattern in screen_processor.py.

        Falls back to the original bytes if PIL is not installed or an error occurs
        so the caller is never left without an image.
        """
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            original_size = img.size

            img.thumbnail((1280, 720), Image.BILINEAR)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=82, optimize=False)
            compressed = buf.getvalue()

            logger.debug(
                "[VISION] Compressed: %dx%d → %dx%d | %d KB → %d KB",
                original_size[0], original_size[1],
                img.size[0], img.size[1],
                len(img_bytes) // 1024,
                len(compressed) // 1024,
            )
            return compressed

        except ImportError:
            logger.debug("[VISION] PIL not installed — skipping compression")
            return img_bytes
        except Exception as e:
            logger.warning("[VISION] Compression failed (using original): %s", e)
            return img_bytes


    def analyze_image(
        self,
        prompt: str,
        img_base64: str,
        chat_history: Optional[List[tuple]] = None,
    ) -> str:

        if not self._groq_clients:
            return "Vision is not available. Please set GROQ_API_KEY."

        if "," in img_base64:
            img_base64 = img_base64.split(",", 1)[-1]

        if not img_base64:
            return "No image data received."

        raw_len = 0

        try:
            raw_len = len(base64.b64decode(img_base64, validate=True))

            if raw_len > VISION_MAX_IMAGE_BYTES:
                logger.warning(
                    "[VISION] Image too large: %d bytes (max %d)", raw_len, VISION_MAX_IMAGE_BYTES
                )
                return "Image is too large. Please use a smaller image."

        except Exception as e:
            logger.warning("[VISION] Invalid base64 image: %s", e)
            return "Invalid image data. Please try again."

        mime = "image/jpeg"
        raw_bytes = base64.b64decode(img_base64)

        try:
            header = raw_bytes[:12]
            if header[:8] == b'\x89PNG\r\n\x1a\n':
                mime = "image/png"
            elif header[:4] == b'RIFF' and header[8:12] == b'WEBP':
                mime = "image/webp"
        except Exception:
            pass

        # Compress to 1280×720 / JPEG 82% to cut token cost and latency
        # (no-op if PIL is not installed; falls back transparently)
        compressed_bytes = self._compress_for_vision(raw_bytes)
        img_base64_compressed = base64.b64encode(compressed_bytes).decode("ascii")
        # Always send as JPEG after compression
        if compressed_bytes is not raw_bytes:
            mime = "image/jpeg"

        user_question = (prompt or "What do you see in this image? Describe it in detail.").strip()
        data_url = f"data:{mime};base64,{img_base64_compressed}"
        logger.info("[VISION] Analyzing image (%d KB raw → %d KB compressed, %s)",
                    len(raw_bytes) // 1024, len(compressed_bytes) // 1024, mime)

        messages = [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_question},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url},
                    },
                ],
            },
        ]

        # Call OpenRouter API
        result = self._call_openrouter(messages)
        if result:
            return result

        return "I couldn't analyze that image. Please try again."

    def _call_openrouter(self, messages: list) -> Optional[str]:
        if not self._openai_client:
            return None
        try:
            response = self._openai_client.chat.completions.create(
                model="nvidia/nemotron-nano-12b-v2-vl:free",
                messages=messages,
                max_tokens=600,
            )
            if response.choices:
                text = (response.choices[0].message.content or "").strip()
                if text:
                    logger.info("[VISION] OpenRouter vision success (%d chars)", len(text))
                    return text
        except Exception as e:
            err_str = str(e).lower()
            if "content_policy" in err_str or "safety" in err_str:
                logger.warning("[VISION] OpenRouter content policy: %s", e)
                return "The image couldn't be analyzed due to content guidelines."
            logger.warning("[VISION] OpenRouter vision error: %s", e)
        return None