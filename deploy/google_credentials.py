"""
Decodes base64-encoded Google credential files from environment variables.
On cloud (Render), files can't persist on disk between deploys.
Solution: base64 encode files → store as env vars → decode at runtime.

To encode on your laptop (run in terminal):
  python -c "import base64; print(base64.b64encode(open('credentials.json','rb').read()).decode())"
  python -c "import base64; print(base64.b64encode(open('database/google_token.json','rb').read()).decode())"

Paste the output as GOOGLE_CREDENTIALS_B64 and GOOGLE_TOKEN_B64 in Render Environment Variables.
"""
import base64
import os
from pathlib import Path
import logging

logger = logging.getLogger("J.A.R.V.I.S")

def restore_google_credentials():
    creds_b64 = os.getenv("GOOGLE_CREDENTIALS_B64", "")
    token_b64 = os.getenv("GOOGLE_TOKEN_B64", "")

    if creds_b64:
        try:
            creds_path = Path("credentials.json")
            creds_path.write_bytes(base64.b64decode(creds_b64))
            logger.info("[CLOUD] credentials.json restored from env var")
        except Exception as e:
            logger.warning("[CLOUD] Could not restore credentials.json: %s", e)

    if token_b64:
        try:
            token_path = Path("database/google_token.json")
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_bytes = base64.b64decode(token_b64)
            token_path.write_bytes(token_bytes)
            logger.info(
                "[CLOUD] google_token.json restored from env var (%d bytes written to %s)",
                len(token_bytes), token_path.resolve()
            )
        except Exception as e:
            logger.warning("[CLOUD] Could not restore google_token.json: %s", e)
