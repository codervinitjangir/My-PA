import logging
import requests
from app.tools.base_tool import BaseTool

logger = logging.getLogger("J.A.R.V.I.S")

class DictionaryPlugin(BaseTool):
    name = "dictionary_lookup"
    description = "Looks up the definition of a word in the dictionary."
    
    def execute(self, word: str, **kwargs) -> dict:
        try:
            resp = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=5)
            if resp.status_code == 200:
                data = resp.json()[0]
                meanings = data.get("meanings", [])
                if meanings:
                    definition = meanings[0]["definitions"][0]["definition"]
                    logger.info(f"[PLUGIN] Dictionary looked up '{word}'")
                    return {"status": "success", "word": word, "definition": definition}
            return {"status": "error", "message": f"Could not find definition for {word}."}
        except Exception as e:
            logger.error(f"[PLUGIN] Dictionary lookup failed: {e}")
            return {"status": "error", "message": str(e)}
