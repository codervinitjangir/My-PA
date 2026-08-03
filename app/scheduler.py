import os
import datetime
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.plugins.calendar_tool import GoogleCalendarTool
from app.plugins.gmail_tool import GmailSummaryTool

logger = logging.getLogger("J.A.R.V.I.S")

LAST_BRIEFING = "No briefing yet."
_scheduler = None
_telegram_app = None   # reference to running telegram Application for proactive jobs


def _classify_google_error(e: Exception) -> tuple:
    """
    Returns (category_str, short_detail_str) for a Google API/auth failure.
    The category string is passed verbatim to the LLM prompt so it can report
    the real cause without fabricating an explanation.

    Categories:
      auth_expired            - refresh token rejected (invalid_grant / revoked)
      auth_missing_credentials - no credentials.json / token file found; headless
                                 server tried to open a browser, which failed
      network_error           - TCP/DNS/timeout connectivity failure
      api_error               - Google API returned an HTTP error (quota, 5xx, etc.)
      unknown                 - anything else
    """
    err_str = str(e).lower()
    raw = str(e)[:200]

    # Auth / token expiry — Google signals these explicitly
    if any(kw in err_str for kw in (
        "invalid_grant", "token has been expired", "token has been revoked",
        "token expired", "refresh error", "oauth", "invalid credentials",
        "auth", "expired", "revoked"
    )):
        return "auth_expired", raw

    # Missing credentials.json or no token → run_local_server() is called
    # → on headless Render this throws "could not locate a runnable browser"
    if any(kw in err_str for kw in (
        "credentials.json", "filenotfounderror", "no such file",
        "runnable browser", "could not locate", "browser"
    )):
        return "auth_missing_credentials", raw

    # Network / connectivity
    if any(kw in err_str for kw in (
        "network", "connection", "timeout", "socket",
        "unreachable", "name or service not known", "gaierror"
    )):
        return "network_error", raw

    # Google API HTTP errors
    if any(kw in err_str for kw in (
        "httperror", "httpexception", "quota", "403", "500", "503"
    )):
        return "api_error", raw

    return f"unknown ({type(e).__name__})", raw


async def generate_briefing(groq_service, memory_service=None):
    global LAST_BRIEFING
    logger.info("[SCHEDULER] Generating morning briefing...")

    # ── Calendar ──────────────────────────────────────────────────────────────────────
    try:
        cal_tool = GoogleCalendarTool()
        calendar_data = cal_tool.execute()
        logger.info("[SCHEDULER] Calendar fetched successfully.")
    except Exception as e:
        cat, detail = _classify_google_error(e)
        calendar_data = f"TOOL_ERROR [calendar]: category={cat} | detail={detail}"
        logger.error("[SCHEDULER] Calendar fetch failed: category=%s | %s", cat, detail)

    # ── Gmail ────────────────────────────────────────────────────────────────────────
    try:
        gmail_tool = GmailSummaryTool()
        gmail_data = gmail_tool.execute()
        logger.info("[SCHEDULER] Gmail fetched successfully.")
    except Exception as e:
        cat, detail = _classify_google_error(e)
        gmail_data = f"TOOL_ERROR [gmail]: category={cat} | detail={detail}"
        logger.error("[SCHEDULER] Gmail fetch failed: category=%s | %s", cat, detail)

    # ── Session summary (Mark-L-inspired: pop once, never repeat) ──────────────────
    session_summary_block = ""
    if memory_service:
        try:
            session_summary = memory_service.pop_latest_session_summary()
            if session_summary:
                session_summary_block = f"Recent Session Snapshot:\n{session_summary}\n\n"
                logger.info("[SCHEDULER] Injecting session summary into briefing.")
        except Exception as e:
            logger.warning("[SCHEDULER] Could not fetch session summary: %s", e)

    # ── Build honest LLM prompt ────────────────────────────────────────────────
    prompt = (
        "You are JARVIS. Generate a concise morning briefing for Boss. "
        "Include: today's schedule, email summary, and one motivational line. "
        "If a 'Recent Session Snapshot' is provided, weave it naturally into the briefing "
        "(e.g., 'Following up on yesterday\'s session...'). "
        "Keep it under 150 words. Speak as JARVIS from Iron Man.\n\n"
        "CRITICAL INSTRUCTION — Error Honesty Rules:\n"
        "  If a data source contains TOOL_ERROR, report the real category you were given:\n"
        "    • auth_expired              → say: the Google authentication token has expired or been revoked\n"
        "    • auth_missing_credentials  → say: re-authentication is required; the server cannot open a browser\n"
        "    • network_error             → say: there was a network connectivity issue reaching Google\n"
        "    • api_error                 → say: the Google API returned an error\n"
        "    • unknown (...)             → say: an unexpected error occurred\n"
        "  NEVER say 'browser issues', 'lost browser connectivity', or invent any reason "
        "that was not explicitly given in the category above. "
        "Use only the exact category label you received.\n\n"
        f"{session_summary_block}"
        f"Schedule:\n{calendar_data}\n\n"
        f"Emails:\n{gmail_data}"
    )

    try:
        briefing = groq_service.get_response(prompt)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        LAST_BRIEFING = f"[{timestamp}]\n{briefing}"

        try:
            from telegram import Bot
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            owner_id = os.getenv("TELEGRAM_OWNER_ID")
            if token and owner_id:
                bot = Bot(token=token)
                await bot.send_message(
                    chat_id=int(owner_id),
                    text=f"\U0001f305 Good morning, Boss.\n\n{LAST_BRIEFING}"
                )
        except Exception as e:
            logger.warning("[TELEGRAM] Failed to push briefing: %s", e)

        logger.info("[SCHEDULER] Morning briefing generated successfully.")
    except Exception as e:
        logger.error("[SCHEDULER] Failed to generate briefing: %s", e)


async def session_idle_checker(chat_service, memory_service, groq_service):
    """
    Runs every 10 minutes. Checks all active sessions for 30+ minutes of
    inactivity and triggers end_session_summary() for idle ones.
    Marks sessions as summarized to avoid double-summarizing.
    """
    import time as _time
    now = _time.time()
    IDLE_THRESHOLD_SEC = 30 * 60  # 30 minutes

    if not hasattr(chat_service, '_session_last_activity'):
        chat_service._session_last_activity = {}
    if not hasattr(chat_service, '_session_summarized'):
        chat_service._session_summarized = set()

    for session_id, messages in list(chat_service.sessions.items()):
        # Skip already-summarized sessions
        if session_id in chat_service._session_summarized:
            continue
        # Skip empty sessions
        if not messages:
            continue

        last_active = chat_service._session_last_activity.get(session_id, 0)
        if last_active == 0:
            continue  # no activity tracked yet — skip

        idle_for = now - last_active
        if idle_for >= IDLE_THRESHOLD_SEC:
            logger.info(
                "[SCHEDULER] Session %s idle for %.0f min — triggering end-of-session summary.",
                session_id[:12],
                idle_for / 60,
            )
            try:
                summary = await __import__('asyncio').to_thread(
                    memory_service.end_session_summary,
                    session_id,
                    messages,
                    groq_service,
                )
                if summary:
                    chat_service._session_summarized.add(session_id)
                    logger.info("[SCHEDULER] End-session summary stored for %s.", session_id[:12])
            except Exception as e:
                logger.error("[SCHEDULER] session_idle_checker error for %s: %s", session_id[:12], e)


async def proactive_check(telegram_app, chat_service, memory_service, groq_service):
    """
    Runs every 5 minutes. Checks if the ProactiveEngine should fire an
    unprompted message to the owner via Telegram.
    """
    if telegram_app is None:
        return

    try:
        proactive_engine = telegram_app.bot_data.get("proactive_engine")
        last_msg_time = telegram_app.bot_data.get("last_telegram_message_time")

        if proactive_engine is None:
            return

        if not proactive_engine.should_trigger(last_msg_time):
            return

        session_id = chat_service.get_or_create_session("telegram")

        import asyncio
        message = await asyncio.to_thread(
            proactive_engine.generate_proactive_message,
            groq_service,
            chat_service,
            session_id,
            memory_service,
        )

        if not message:
            return

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        owner_id = os.getenv("TELEGRAM_OWNER_ID")
        if token and owner_id:
            from telegram import Bot
            bot = Bot(token=token)
            await bot.send_message(chat_id=int(owner_id), text=message)
            # Mark AFTER confirmed delivery — a send failure won't eat the cooldown
            proactive_engine.mark_triggered()
            logger.info("[PROACTIVE] Sent unprompted message to owner.")

    except Exception as e:
        logger.error("[SCHEDULER] proactive_check failed: %s", e)


def init_scheduler(groq_service, memory_service=None, chat_service=None, telegram_app=None):
    global _scheduler, _telegram_app
    if _scheduler is not None:
        return

    _telegram_app = telegram_app

    timezone = os.getenv("TIMEZONE", "Asia/Kolkata")
    _scheduler = AsyncIOScheduler(timezone=timezone)

    # Schedule job at 08:00 every day
    _scheduler.add_job(
        generate_briefing,
        'cron',
        hour=8,
        minute=0,
        args=[groq_service, memory_service],
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

    # Self-diagnostic job every 30 minutes
    from app.services.self_diagnostic import global_diagnostic_service
    _scheduler.add_job(
        global_diagnostic_service.run_diagnostic,
        "interval",
        minutes=30,
        id="self_diagnostic",
        replace_existing=True,
    )
    logger.info("[SCHEDULER] Self-diagnostic job scheduled every 30 minutes")

    # Session-end idle checker: every 10 min, summarizes sessions idle 30+ min
    if memory_service and chat_service:
        _scheduler.add_job(
            session_idle_checker,
            "interval",
            minutes=10,
            args=[chat_service, memory_service, groq_service],
            id="session_idle_checker",
            replace_existing=True,
        )
        logger.info("[SCHEDULER] Session idle checker scheduled every 10 minutes")

    # Proactive engine check: every 5 min, fires unprompted Telegram message if needed
    if telegram_app is not None and chat_service and memory_service:
        _scheduler.add_job(
            proactive_check,
            "interval",
            minutes=5,
            args=[telegram_app, chat_service, memory_service, groq_service],
            id="proactive_check",
            replace_existing=True,
        )
        logger.info("[SCHEDULER] Proactive engine check scheduled every 5 minutes")

    _scheduler.start()
    logger.info("[SCHEDULER] APScheduler started. Daily briefing set for 08:00 %s.", timezone)


def shutdown_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("[SCHEDULER] APScheduler shut down.")
