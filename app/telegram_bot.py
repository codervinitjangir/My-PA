import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from app.plugins.calendar_tool import GoogleCalendarTool
from app.plugins.gmail_tool import GmailSummaryTool
import app.scheduler
from jarvis_os.observers.screen_observer import ScreenObserver, CooldownError

logger = logging.getLogger("J.A.R.V.I.S.Telegram")

def check_owner(update: Update) -> bool:
    owner_id_str = os.getenv("TELEGRAM_OWNER_ID")
    if not owner_id_str:
        return False
    try:
        owner_id = int(owner_id_str)
    except ValueError:
        return False
        
    if update.effective_user and update.effective_user.id == owner_id:
        return True
    return False

def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not check_owner(update):
            logger.warning(f"[TELEGRAM] Unauthorized access attempt from {update.effective_user.id if update.effective_user else 'Unknown'}")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

@owner_only
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Good day, Sir. J.A.R.V.I.S online. Send me anything or use /brief, /cal, /mail.")

@owner_only
async def brief_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    briefing = app.scheduler.LAST_BRIEFING
    if not briefing or "No briefing yet" in briefing:
        await update.message.reply_text("No briefing generated yet, Sir. Check back at 08:00.")
    else:
        await update.message.reply_text(briefing)

@owner_only
async def cal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tool = GoogleCalendarTool()
        result = tool.execute()
        await update.message.reply_text(result[:4090] if result else "No calendar data found.")
    except Exception as e:
        await update.message.reply_text(f"Error fetching calendar: {e}")

@owner_only
async def mail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tool = GmailSummaryTool()
        result = tool.execute()
        await update.message.reply_text(result[:4090] if result else "No mail data found.")
    except Exception as e:
        await update.message.reply_text(f"Error fetching mail: {e}")

import asyncio
import webbrowser

def consume_jarvis_stream(chat_service, session_id, text):
    stream = chat_service.process_jarvis_message_stream(session_id, text)
    full_response = ""
    links = []
    for chunk in stream:
        if isinstance(chunk, str):
            full_response += chunk
        elif isinstance(chunk, dict) and "actions" in chunk:
            actions = chunk["actions"]
            for key in ["wopens", "plays", "googlesearches", "youtubesearches"]:
                if actions.get(key):
                    for url in actions[key]:
                        links.append(url)
                        try:
                            webbrowser.open(url)
                        except Exception as e:
                            logger.error(f"[TELEGRAM] Failed to open URL on host PC: {e}")
            if actions.get("images"):
                links.extend(actions["images"])
                    
    if links:
        full_response += "\n\nHere are your links:\n" + "\n".join(links)
        
    return full_response

@owner_only
async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_service = context.application.bot_data.get("chat_service")
    if not chat_service:
        await update.message.reply_text("Error: ChatService not available.")
        return
        
    user_text = update.message.text
    try:
        session_id = chat_service.get_or_create_session("telegram")
        response = await asyncio.to_thread(consume_jarvis_stream, chat_service, session_id, user_text)
        await update.message.reply_text(response[:4090] if response else "No response generated.")
    except Exception as e:
        await update.message.reply_text(f"Error processing message: {e}")

@owner_only
async def screen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capture and analyze current screen, update GlobalStateManager, reply with summary."""
    await update.message.reply_text("Analyzing your screen, Sir...")
    try:
        from app.services.vision_service import VisionService
        from app.main import _state_mgr, _SCREEN_PROMPT

        observer = ScreenObserver()
        image_bytes = observer.capture_screen()
        img_b64 = observer.sanitize_data(image_bytes)
        del image_bytes

        vision = VisionService()
        raw_text = vision.analyze_image(prompt=_SCREEN_PROMPT, img_base64=img_b64)
        del img_b64

        screen_state = observer.parse_response(raw_text)
        _state_mgr.update_runtime_state("screen", screen_state.model_dump())

        reply = (
            f"Screen analyzed, Sir.\n\n"
            f"App: {screen_state.application}\n"
            f"Activity: {screen_state.activity}\n"
            f"Confidence: {screen_state.confidence:.0f}%\n"
            f"Summary: {screen_state.summary}\n"
            f"Suggestion: {screen_state.next_best_action}"
        )
        await update.message.reply_text(reply)

    except CooldownError as e:
        await update.message.reply_text(f"Cooldown active, Sir. {e}")
    except Exception as e:
        await update.message.reply_text(f"Screen analysis failed: {e}")

async def start_telegram_bot(chat_service):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.warning("[TELEGRAM] Bot token not set, skipping.")
        return None
        
    application = ApplicationBuilder().token(token).build()
    application.bot_data["chat_service"] = chat_service
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("brief", brief_command))
    application.add_handler(CommandHandler("cal", cal_command))
    application.add_handler(CommandHandler("mail", mail_command))
    application.add_handler(CommandHandler("screen", screen_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("[TELEGRAM] Bot started successfully.")
    return application

async def stop_telegram_bot(application):
    if application:
        logger.info("[TELEGRAM] Stopping bot...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("[TELEGRAM] Bot stopped.")
