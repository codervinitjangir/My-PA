import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from app.plugins.calendar_tool import GoogleCalendarTool
from app.plugins.gmail_tool import GmailSummaryTool
import app.scheduler

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

def consume_jarvis_stream(chat_service, session_id, text):
    stream = chat_service.process_jarvis_message_stream(session_id, text)
    full_response = ""
    for chunk in stream:
        if isinstance(chunk, str):
            full_response += chunk
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
