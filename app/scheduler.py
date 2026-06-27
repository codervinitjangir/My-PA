import os
import datetime
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.plugins.calendar_tool import GoogleCalendarTool
from app.plugins.gmail_tool import GmailSummaryTool

logger = logging.getLogger("J.A.R.V.I.S")

LAST_BRIEFING = "No briefing yet."
_scheduler = None

async def generate_briefing(groq_service):
    global LAST_BRIEFING
    logger.info("[SCHEDULER] Generating morning briefing...")
    
    try:
        cal_tool = GoogleCalendarTool()
        calendar_data = cal_tool.execute()
    except Exception as e:
        calendar_data = f"Error fetching calendar: {e}"
        
    try:
        gmail_tool = GmailSummaryTool()
        gmail_data = gmail_tool.execute()
    except Exception as e:
        gmail_data = f"Error fetching emails: {e}"
        
    prompt = (
        "You are JARVIS. Generate a concise morning briefing for Sir. "
        "Include: today's schedule, email summary, and one motivational line. "
        "Keep it under 120 words. Speak as JARVIS from Iron Man.\n\n"
        f"Schedule:\n{calendar_data}\n\n"
        f"Emails:\n{gmail_data}"
    )
    
    try:
        # We need to await or call the correct method on GroqService
        # GroqProvider doesn't have an async get_response, but it's synchronous in langchain.
        # However, wait, let's check GroqService method.
        # Actually, if it's synchronous, we can just call it or run it in a thread.
        # But get_response returns str. Let's just call it.
        briefing = groq_service.get_response(prompt)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        LAST_BRIEFING = f"[{timestamp}]\n{briefing}"
        
        try:
            import os
            from telegram import Bot
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            owner_id = os.getenv("TELEGRAM_OWNER_ID")
            if token and owner_id:
                bot = Bot(token=token)
                await bot.send_message(chat_id=int(owner_id), text=f"🌅 Good morning, Sir.\n\n{LAST_BRIEFING}")
        except Exception as e:
            logger.warning(f"[TELEGRAM] Failed to push briefing: {e}")
            
        logger.info("[SCHEDULER] Morning briefing generated successfully.")
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to generate briefing: {e}")

def init_scheduler(groq_service):
    global _scheduler
    if _scheduler is not None:
        return
        
    timezone = os.getenv("TIMEZONE", "Asia/Kolkata")
    _scheduler = AsyncIOScheduler(timezone=timezone)
    
    # Schedule job at 08:00 every day
    _scheduler.add_job(
        generate_briefing,
        'cron',
        hour=8,
        minute=0,
        args=[groq_service],
        id='morning_briefing',
        replace_existing=True
    )
    
    # Keep-alive ping every 10 minutes (prevents Render free tier sleep)
    from deploy.keep_alive import keep_alive_ping
    _scheduler.add_job(
        keep_alive_ping,
        "interval",
        minutes=10,
        id="keep_alive",
        replace_existing=True,
    )
    logger.info("[SCHEDULER] Keep-alive ping scheduled every 10 minutes")
    
    _scheduler.start()
    logger.info(f"[SCHEDULER] APScheduler started. Daily briefing set for 08:00 {timezone}.")

def shutdown_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("[SCHEDULER] APScheduler shut down.")
