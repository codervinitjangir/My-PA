import logging
import os
import asyncio
from typing import Optional
from app.tools.base_tool import BaseTool

logger = logging.getLogger("J.A.R.V.I.S")

class AdvancedBrowserTool(BaseTool):
    name = "advanced_browser"
    description = "Advanced browser automation tool using browser-use framework. Navigates, scrapes, and automates tasks on the web."
    
    def execute(self, task: str, url: Optional[str] = None, **kwargs) -> dict:
        logger.info(f"[BROWSER] Task: {task} | URL: {url}")
        
        try:
            from browser_use import Agent
            from langchain_groq import ChatGroq
            from config import GROQ_API_KEYS
        except ImportError:
            logger.warning("[BROWSER] browser-use or langchain-groq is not installed. Falling back to OS open.")
            if url:
                try:
                    os.startfile(url)
                    return {"status": "success", "message": f"Opened {url} via OS fallback."}
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            return {"status": "error", "message": "browser-use package is missing and no URL provided for fallback."}

        async def run_browser_task():
            api_key = GROQ_API_KEYS[0] if GROQ_API_KEYS else os.getenv("GROQ_API_KEY")
            llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=api_key)
            
            full_task = f"Go to {url} and " + task if url else task
            
            agent = Agent(
                task=full_task,
                llm=llm
            )
            history = await agent.run()
            return history.final_result()

        try:
            result = asyncio.run(run_browser_task())
            logger.info("[BROWSER] Task completed successfully.")
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"[BROWSER] Task failed: {e}")
            return {"status": "error", "message": str(e)}
