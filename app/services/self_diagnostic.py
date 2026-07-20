import os
import re
import json
import uuid
import logging
import asyncio
import subprocess
from pathlib import Path

from app.services.error_tracker import global_error_tracker
from app.providers.gemini_provider import GeminiProvider

logger = logging.getLogger("J.A.R.V.I.S")

class SelfDiagnosticService:
    def __init__(self):
        self.pending_fixes = {}  # fix_id -> fix_data
        self.provider = None

    def _get_provider(self):
        if not self.provider:
            self.provider = GeminiProvider(vector_store=None)
        return self.provider

    def _get_project_files_from_tb(self, tb_text: str) -> list:
        """Extract valid local file paths from a traceback string."""
        files = set()
        if not tb_text:
            return []
            
        matches = re.findall(r'File "(.*?)", line \d+', tb_text)
        for match in matches:
            # Clean up path and check if it exists
            file_path = os.path.abspath(match)
            # Only include our own files (not stdlib or site-packages unless they're local)
            # A simple heuristic: check if it's in the same directory tree as this file
            app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            if file_path.startswith(app_dir) and os.path.exists(file_path):
                files.add(file_path)
        return list(files)

    async def run_diagnostic(self):
        """Background job to check for recurring errors and propose fixes."""
        logger.info("[SELF-DIAGNOSTIC] Running diagnostic check...")
        recurring_errors = global_error_tracker.get_recurring_errors(threshold=3, timeframe_minutes=60)
        
        if not recurring_errors:
            logger.info("[SELF-DIAGNOSTIC] No recurring errors found.")
            return

        for error in recurring_errors:
            identifier = error["identifier"]
            
            # Check if we already have a pending fix for this error
            already_pending = any(f["identifier"] == identifier for f in self.pending_fixes.values())
            if already_pending:
                continue
                
            await self._diagnose_and_propose(error)

    async def _diagnose_and_propose(self, error: dict):
        tb_text = error["traceback"]
        files = self._get_project_files_from_tb(tb_text)
        
        file_contents = ""
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Prepend line numbers for better LLM context
                    numbered_content = "\n".join([f"{i+1}: {line}" for i, line in enumerate(content.splitlines())])
                    file_contents += f"\n--- FILE: {file_path} ---\n{numbered_content}\n"
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")

        prompt = f"""
You are an expert Python debugger and AI assistant core developer.
A recurring error has been detected in the system.

ERROR TRACEBACK:
{tb_text}

ERROR MESSAGE:
{error['message']}

RELEVANT FILES:
{file_contents}

Your task is to:
1. Diagnose the root cause of the error.
2. Propose a minimal, safe fix.
3. Return the exact `target_content` (the block of code to replace) and the `replacement_content`.
Ensure the `target_content` EXACTLY matches the existing code in the file, including indentation, so a simple string replacement will work. Do NOT include line numbers in your target_content or replacement_content.

Respond ONLY with a valid JSON object in this format (no markdown code blocks, no other text):
{{
  "diagnosis": "Short explanation of the issue",
  "file_path": "Absolute path to the file to modify",
  "target_content": "exact string to replace",
  "replacement_content": "new string to insert"
}}
"""
        provider = self._get_provider()
        try:
            # We run this in a thread since get_response is likely synchronous
            response_text = await asyncio.to_thread(provider.get_response, prompt)
            
            # Clean up potential markdown formatting from LLM
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
                
            fix_data = json.loads(response_text.strip())
            fix_data["identifier"] = error["identifier"]
            
            fix_id = str(uuid.uuid4())[:8]
            self.pending_fixes[fix_id] = fix_data
            
            await self._notify_telegram(fix_id, error["message"], fix_data)
            
        except Exception as e:
            logger.error(f"[SELF-DIAGNOSTIC] Failed to generate or parse fix: {e}")

    async def _notify_telegram(self, fix_id: str, error_msg: str, fix_data: dict):
        try:
            from telegram import Bot
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            owner_id = os.getenv("TELEGRAM_OWNER_ID")
            if token and owner_id:
                bot = Bot(token=token)
                
                message = (
                    f"⚠️ **Recurring Error Detected**\n"
                    f"`{error_msg[:100]}...`\n\n"
                    f"🧠 **Diagnosis**\n{fix_data.get('diagnosis', 'Unknown')}\n\n"
                    f"🛠️ **Proposed Fix** in `{os.path.basename(fix_data.get('file_path', 'unknown'))}`:\n"
                    f"```diff\n"
                    f"- {fix_data.get('target_content', '').strip()}\n"
                    f"+ {fix_data.get('replacement_content', '').strip()}\n"
                    f"```\n\n"
                    f"Reply `/apply_fix {fix_id}` to apply and commit."
                )
                await bot.send_message(chat_id=int(owner_id), text=message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"[SELF-DIAGNOSTIC] Telegram notification failed: {e}")

    def apply_fix(self, fix_id: str) -> str:
        """Applies a pending fix and commits to git."""
        if fix_id not in self.pending_fixes:
            return f"Error: No pending fix found with ID {fix_id}."
            
        fix_data = self.pending_fixes[fix_id]
        file_path = fix_data.get("file_path")
        target = fix_data.get("target_content")
        replacement = fix_data.get("replacement_content")
        
        if not file_path or not os.path.exists(file_path):
            return f"Error: File path invalid or does not exist: {file_path}"
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            if target not in content:
                # Fallback: maybe line endings are different
                target_norm = target.replace("\r\n", "\n")
                content_norm = content.replace("\r\n", "\n")
                if target_norm in content_norm:
                    content = content_norm.replace(target_norm, replacement)
                else:
                    return "Error: Target content could not be found exactly in the file. The file may have changed or the LLM hallucinated the spacing."
            else:
                content = content.replace(target, replacement)
                
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            # Git commit
            try:
                subprocess.run(["git", "add", file_path], check=True, cwd=os.path.dirname(file_path))
                commit_msg = f"Auto-fix applied for {os.path.basename(file_path)}\n\nDiagnosis: {fix_data.get('diagnosis')}"
                subprocess.run(["git", "commit", "-m", commit_msg], check=True, cwd=os.path.dirname(file_path))
                git_status = "Successfully committed to git."
            except Exception as e:
                git_status = f"Applied to file, but git commit failed: {e}"
                
            del self.pending_fixes[fix_id]
            
            return f"Success! Fix applied to {os.path.basename(file_path)}. {git_status}"
            
        except Exception as e:
            return f"Error applying fix: {e}"

# Global instance
global_diagnostic_service = SelfDiagnosticService()
