import os
import logging
from app.tools.base_tool import BaseTool

logger = logging.getLogger("J.A.R.V.I.S")

class PlayMusicTool(BaseTool):
    name = "play_music"
    description = "Plays music by launching a browser search or using pywhatkit if available."
    
    def execute(self, song_name: str, **kwargs) -> dict:
        try:
            import pywhatkit
            logger.info(f"[MEDIA] Playing '{song_name}' on YouTube via pywhatkit.")
            pywhatkit.playonyt(song_name)
            return {"status": "success", "message": f"Playing {song_name} on YouTube"}
        except ImportError:
            logger.warning("[MEDIA] pywhatkit not installed, falling back to browser search.")
            # Fallback to standard OS URL launch
            url = f"https://www.youtube.com/results?search_query={song_name.replace(' ', '+')}"
            try:
                os.startfile(url)
                return {"status": "success", "message": f"Opened YouTube search for {song_name}"}
            except Exception as e:
                return {"status": "error", "message": f"Failed to open browser: {e}"}
        except Exception as e:
            logger.error(f"[MEDIA] Failed to play music: {e}")
            return {"status": "error", "message": str(e)}
