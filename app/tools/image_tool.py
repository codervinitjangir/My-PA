import time
import logging
from urllib.parse import quote
import httpx
from app.tools.base_tool import BaseTool

logger = logging.getLogger("J.A.R.V.I.S")

class ImageGenerationTool(BaseTool):
    name = "generate_image"
    description = "Generates an image using Pollinations.ai"

    def execute(self, prompt: str, **kwargs) -> tuple:
        if not prompt or len(prompt) < 3:
            logger.warning("[TOOL] Image prompt too short (< 3 chars)")
            return None
            
        prompt = prompt[:4000]
        t0 = time.perf_counter()
        
        encoded_prompt = quote(prompt, safe='')
        api_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?model=flux&width=1024&height=1024&nologo=true&private=true&enhance=true&safe=false"
        )
        logger.info("[TOOL] Fetching Pollinations image: %s", api_url[:120])
        
        for attempt in range(3):
            try:
                with httpx.Client(timeout=60, follow_redirects=True) as client:
                    resp = client.get(api_url)
                    if resp.status_code == 200 and resp.content:
                        content_type = resp.headers.get("content-type", "")
                        if "image" in content_type or len(resp.content) > 1000:
                            logger.info("[TOOL] Pollinations image fetched (%d bytes) in %.2fs", len(resp.content), time.perf_counter() - t0)
                            return (api_url, resp.content)
                        logger.warning("[TOOL] Pollinations attempt %d: status=%d", attempt + 1, resp.status_code)
            except Exception as e:
                logger.warning("[TOOL] Pollinations attempt %d failed: %s", attempt + 1, e)
            time.sleep(2)
            
        return None
