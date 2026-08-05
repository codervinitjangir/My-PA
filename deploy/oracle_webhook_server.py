import os
import subprocess
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException
import uvicorn

app = FastAPI(title="JARVIS Oracle Webhook Server")

GITHUB_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

@app.post("/webhook")
async def github_webhook(request: Request):
    if GITHUB_SECRET:
        signature = request.headers.get("X-Hub-Signature-256")
        if not signature:
            raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")
            
        body = await request.body()
        expected_signature = "sha256=" + hmac.new(
            GITHUB_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Run git pull and restart via PM2
    try:
        # Move to the root of the project to pull
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        # Git pull
        subprocess.run(["git", "pull", "origin", "main"], cwd=project_root, check=True)
        
        # Restart JARVIS via PM2
        # Assuming the PM2 process is named "jarvis"
        subprocess.run(["pm2", "restart", "jarvis"], check=True)
        
        return {"status": "success", "message": "Successfully pulled latest code and restarted JARVIS."}
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Update/Restart failed: {str(e)}")

if __name__ == "__main__":
    # Run on a different port than the main JARVIS application (8000)
    # E.g., open port 8001 in Oracle Security Lists and ufw for this webhook
    uvicorn.run(app, host="0.0.0.0", port=8001)
