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
    await update.message.reply_text("Good day, Boss. J.A.R.V.I.S online. Send me anything or use /brief, /cal, /mail.\n/sendfile pdf — get latest PDF from Gmail or Downloads")

@owner_only
async def brief_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    briefing = app.scheduler.LAST_BRIEFING
    if not briefing or "No briefing yet" in briefing:
        await update.message.reply_text("No briefing generated yet, Boss. Check back at 08:00.")
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

@owner_only
async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory_service = context.application.bot_data.get("memory_service")
    if not memory_service:
        await update.message.reply_text("Memory service is offline.")
        return
    text = memory_service.get_all_knowledge()
    await update.message.reply_text(text[:4090])

@owner_only
async def forget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory_service = context.application.bot_data.get("memory_service")
    if not memory_service:
        await update.message.reply_text("Memory service is offline.")
        return
    keyword = " ".join(context.args).strip().lower()
    if not keyword:
        await update.message.reply_text("Usage: /forget [keyword] or /forget all")
        return
    if keyword == "all":
        res = memory_service.forget_all()
    else:
        res = memory_service.forget_knowledge(keyword)
    await update.message.reply_text(res)

@owner_only
async def apply_fix_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /apply_fix <fix_id>")
        return
    
    fix_id = context.args[0]
    from app.services.self_diagnostic import global_diagnostic_service
    
    # Run the application (which includes I/O and git operations) in a thread
    import asyncio
    result = await asyncio.to_thread(global_diagnostic_service.apply_fix, fix_id)
    await update.message.reply_text(result)

import asyncio
import webbrowser
import tempfile
from pathlib import Path
from app.plugins.file_finder_tool import FileFinderTool

async def send_file_to_telegram(bot, chat_id, file_bytes, filename, caption):
    """
    Sends a file to Telegram using bot.send_document().
    file_bytes: raw bytes
    filename: display name shown in Telegram
    caption: short message shown above the file
    Uses tempfile.NamedTemporaryFile — deleted automatically after send.
    Max file size check: if len(file_bytes) > 50 * 1024 * 1024, reply with size error.
    """
    if len(file_bytes) > 50 * 1024 * 1024:
        await bot.send_message(chat_id=chat_id, text=f"File {filename} is too large (>50MB) for Telegram.")
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
        temp_file.write(file_bytes)
        temp_file_path = temp_file.name

    try:
        with open(temp_file_path, 'rb') as f:
            await bot.send_document(chat_id=chat_id, document=f, filename=filename, caption=caption)
    except Exception as e:
        logger.error(f"[TELEGRAM] Failed to send file: {e}")
        await bot.send_message(chat_id=chat_id, text=f"Error sending file: {e}")
    finally:
        try:
            os.remove(temp_file_path)
        except Exception as e:
            logger.error(f"[TELEGRAM] Failed to delete temp file {temp_file_path}: {e}")

@owner_only
async def sendfile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Usage: /sendfile pdf          → finds latest PDF attachment in Gmail, sends it
           /sendfile report.pdf   → finds report.pdf in local filesystem, sends it
           /sendfile              → replies with usage instructions
    """
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage:\n/sendfile pdf — latest PDF from Gmail\n/sendfile filename.pdf — local file search"
        )
        return

async def do_sendfile_logic(query: str, bot, chat_id, reply_func):
    await reply_func(f"Looking for '{query}', Boss...")

    common_types = ["pdf", "docx", "xlsx", "zip", "png", "jpg", "jpeg", "txt", "csv"]

    if query in common_types:
        # Gmail first
        tool = GmailSummaryTool()
        result = await asyncio.to_thread(tool.get_latest_attachment, file_type=query)
        if result.get("found"):
            caption = f"📎 From: {result['sender']}\n📧 Subject: {result['subject']}\n📦 Size: {result['size_mb']:.1f} MB"
            await send_file_to_telegram(bot, chat_id, result['data'], result['filename'], caption)
            return
        # fallback to local
        finder = FileFinderTool()
        local = await asyncio.to_thread(finder.execute, file_type=query)
    else:
        # Local first
        finder = FileFinderTool()
        local = await asyncio.to_thread(finder.execute, filename=query)
        if not local.get("found"):
            # fallback to Gmail
            ext = query.split(".")[-1] if "." in query else query
            tool = GmailSummaryTool()
            result = await asyncio.to_thread(tool.get_latest_attachment, file_type=ext)
            if result.get("found"):
                caption = f"📎 From Gmail: {result['sender']}\n📦 {result['size_mb']:.1f} MB"
                await send_file_to_telegram(bot, chat_id, result['data'], result['filename'], caption)
                return
            await reply_func(f"Could not find '{query}' locally or in Gmail, Boss.")
            return

    if local.get("found"):
        file_path = Path(local["path"])
        file_bytes = await asyncio.to_thread(file_path.read_bytes)
        caption = f"📁 From local: {local['filename']}\n📦 {local['size_mb']:.1f} MB"
        await send_file_to_telegram(bot, chat_id, file_bytes, local["filename"], caption)
    else:
        await reply_func(f"Nothing found for '{query}', Boss.")


@owner_only
async def sendfile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Usage: /sendfile pdf          → finds latest PDF attachment in Gmail, sends it
           /sendfile report.pdf   → finds report.pdf in local filesystem, sends it
           /sendfile              → replies with usage instructions
    """
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage:\n/sendfile pdf — latest PDF from Gmail\n/sendfile filename.pdf — local file search"
        )
        return

    query = args[0].lower()
    await do_sendfile_logic(query, context.bot, update.effective_chat.id, update.message.reply_text)

def background_sendfile(query: str):
    """Entry point for triggering a file send from outside the telegram bot context (e.g., from web UI)."""
    import os
    from telegram import Bot
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    owner_id_str = os.getenv("TELEGRAM_OWNER_ID")
    if not bot_token or not owner_id_str:
        logger.error("[TELEGRAM] Missing bot token or owner ID for background sendfile.")
        return
        
    async def run_it():
        bot = Bot(token=bot_token)
        chat_id = int(owner_id_str)
        
        async def dummy_reply(text):
            await bot.send_message(chat_id=chat_id, text=text)
            
        try:
            await do_sendfile_logic(query, bot, chat_id, dummy_reply)
        except Exception as e:
            logger.error(f"[TELEGRAM] Background sendfile error: {e}")
            
    asyncio.run(run_it())


def consume_jarvis_stream(chat_service, session_id, text, imgbase64=None):
    stream = chat_service.process_jarvis_message_stream(session_id, text, imgbase64)
    full_response = ""
    links = []
    final_actions = {}
    for chunk in stream:
        if isinstance(chunk, str):
            full_response += chunk
        elif isinstance(chunk, dict) and "actions" in chunk:
            actions = chunk["actions"]
            if "sendfile" in actions:
                final_actions["sendfile"] = actions["sendfile"]
            for key in ["wopens", "plays", "googlesearches", "youtubesearches"]:
                if actions.get(key):
                    for url in actions[key]:
                        links.append(url)
                        try:
                            from config import IS_CLOUD
                            if IS_CLOUD:
                                from app.websocket_manager import laptop_manager
                                laptop_manager.send_and_wait(action="open_url", payload={"url": url})
                            else:
                                webbrowser.open(url)
                        except Exception as e:
                            logger.error(f"[TELEGRAM] Failed to open URL on host PC: {e}")
            if actions.get("images"):
                links.extend(actions["images"])
                    
    if links:
        full_response += "\n\nHere are your links:\n" + "\n".join(links)
        
    logger.info(f"[TELEGRAM] Sending response: {full_response}")
    return full_response, final_actions

class DummyContext:
    def __init__(self, bot, args):
        self.bot = bot
        self.args = args

@owner_only
async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_service = context.application.bot_data.get("chat_service")
    if not chat_service:
        await update.message.reply_text("Error: ChatService not available.")
        return
        
    user_text = update.message.text
    from app.utils.wake_word_utils import strip_wake_word
    user_text = strip_wake_word(user_text)
    
    try:
        session_id = chat_service.get_or_create_session("telegram")
        response, actions = await asyncio.to_thread(consume_jarvis_stream, chat_service, session_id, user_text)
        if response:
            await update.message.reply_text(response[:4090])
        
        if "sendfile" in actions:
            query = actions["sendfile"]
            dummy_ctx = DummyContext(context.bot, [query])
            await sendfile_command(update, dummy_ctx)
    except Exception as e:
        await update.message.reply_text(f"Error processing message: {e}")

@owner_only
async def screen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capture and analyze current screen, update GlobalStateManager, reply with summary."""
    await update.message.reply_text("Analyzing your screen, Boss...")
    try:
        from app.services.vision_service import VisionService
        from app.main import _state_mgr, _SCREEN_PROMPT

        from config import IS_CLOUD
        observer = ScreenObserver()
        
        if IS_CLOUD:
            from app.websocket_manager import laptop_manager
            resp = await laptop_manager.send_and_wait_async(action="screenshot", timeout=20)
            if resp.get("status") != "success":
                await update.message.reply_text(f"Could not reach laptop: {resp.get('message')}")
                return
            img_b64 = f"data:image/jpeg;base64,{resp.get('image_b64')}"
        else:
            image_bytes = observer.capture_screen()
            img_b64 = observer.sanitize_data(image_bytes)
            del image_bytes

        vision = VisionService()
        raw_text = vision.analyze_image(prompt=_SCREEN_PROMPT, img_base64=img_b64)

        screen_state = observer.parse_response(raw_text)
        _state_mgr.update_runtime_state("screen", screen_state.model_dump())

        import base64
        raw_b64 = img_b64.split(",")[1] if "," in img_b64 else img_b64
        image_bytes_decoded = base64.b64decode(raw_b64)
        del img_b64

        reply = (
            f"Screen analyzed, Boss.\n\n"
            f"App: {screen_state.application}\n"
            f"Activity: {screen_state.activity}\n"
            f"Confidence: {screen_state.confidence:.0f}%\n"
            f"Summary: {screen_state.summary}\n"
            f"Suggestion: {screen_state.next_best_action}"
        )
        await update.message.reply_photo(photo=image_bytes_decoded)
        await update.message.reply_text(reply)

    except CooldownError as e:
        await update.message.reply_text(f"Cooldown active, Boss. {e}")
    except Exception as e:
        await update.message.reply_text(f"Screen analysis failed: {e}")

@owner_only
async def press_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Press a keyboard shortcut on the laptop."""
    if not context.args:
        await update.message.reply_text("Usage: /press <shortcut> (e.g. ctrl+s)")
        return
    shortcut = " ".join(context.args)
    from config import IS_CLOUD
    if IS_CLOUD:
        from app.websocket_manager import laptop_manager
        resp = await laptop_manager.send_and_wait_async("keyboard_shortcut", {"shortcut": shortcut})
        await update.message.reply_text(resp.get("message", "Sent shortcut command"))
    else:
        try:
            import keyboard
            keyboard.send(shortcut)
            await update.message.reply_text(f"Pressed {shortcut}")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

@owner_only
async def type_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Type text on the laptop."""
    if not context.args:
        await update.message.reply_text("Usage: /type <text>")
        return
    text = " ".join(context.args)
    from config import IS_CLOUD
    if IS_CLOUD:
        from app.websocket_manager import laptop_manager
        resp = await laptop_manager.send_and_wait_async("type_text", {"text": text})
        await update.message.reply_text(resp.get("message", "Sent type command"))
    else:
        try:
            import keyboard
            keyboard.write(text, delay=0.01)
            await update.message.reply_text("Typed text")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

@owner_only
async def scroll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scroll on the laptop."""
    if not context.args:
        await update.message.reply_text("Usage: /scroll <up|down> [amount]")
        return
    direction = context.args[0].lower()
    if direction not in ["up", "down"]:
        await update.message.reply_text("Direction must be 'up' or 'down'")
        return
    amount = 500
    if len(context.args) > 1:
        try:
            amount = int(context.args[1])
        except ValueError:
            await update.message.reply_text("Amount must be a number")
            return
            
    from config import IS_CLOUD
    if IS_CLOUD:
        from app.websocket_manager import laptop_manager
        resp = await laptop_manager.send_and_wait_async("scroll", {"direction": direction, "amount": amount})
        await update.message.reply_text(resp.get("message", "Sent scroll command"))
    else:
        try:
            import pyautogui
            scroll_amount = amount if direction == "up" else -amount
            pyautogui.scroll(scroll_amount)
            await update.message.reply_text(f"Scrolled {direction} by {amount}")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

@owner_only
async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_service = context.application.bot_data.get("chat_service")
    if not chat_service:
        await update.message.reply_text("Error: ChatService not available.")
        return
        
    args = context.args
    session_id = "telegram"
    from config import PRESETS
    
    if not args:
        current = chat_service.session_presets.get(session_id, getattr(chat_service, 'current_preset', 'default'))
        available = ", ".join(PRESETS.keys())
        await update.message.reply_text(f"Current mode: {current}\nAvailable modes: {available}")
        return
        
    new_mode = args[0].lower()
    if new_mode in PRESETS:
        chat_service.set_preset(new_mode, session_id)
        await update.message.reply_text(f"Switched to {new_mode} mode, Sir.")
    else:
        await update.message.reply_text(f"Unknown mode: {new_mode}. Available modes: {', '.join(PRESETS.keys())}")

@owner_only
async def photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_service = context.application.bot_data.get("chat_service")
    if not chat_service:
        await update.message.reply_text("Error: ChatService not available.")
        return
        
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        byte_array = await file.download_as_bytearray()
        
        import base64
        img_b64 = base64.b64encode(byte_array).decode('utf-8')
        img_b64 = f"data:image/jpeg;base64,{img_b64}"
        
        user_text = update.message.caption or "What is in this image?"
        
        session_id = chat_service.get_or_create_session("telegram")
        response, actions = await asyncio.to_thread(consume_jarvis_stream, chat_service, session_id, user_text, img_b64)
        if response:
            await update.message.reply_text(response[:4090])
        else:
            await update.message.reply_text("No response generated.")
            
        if "sendfile" in actions:
            query = actions["sendfile"]
            dummy_ctx = DummyContext(context.bot, [query])
            await sendfile_command(update, dummy_ctx)
    except Exception as e:
        logger.error(f"[TELEGRAM] Error processing photo: {e}", exc_info=True)
        await update.message.reply_text("Sorry, I encountered an error processing your photo.")

async def start_telegram_bot(chat_service):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.warning("[TELEGRAM] Bot token not set, skipping.")
        return None

    # ── Conflict Guard ──────────────────────────────────────────────────────
    # When running locally while a Render server is also live, avoid the
    # 409 "Conflict: terminated by other getUpdates request" spam by checking
    # if another polling session is active. If so, skip local polling.
    from config import IS_CLOUD
    if not IS_CLOUD:
        skip_polling = os.getenv("TELEGRAM_SKIP_POLLING", "false").lower() == "true"
        if skip_polling:
            logger.info("[TELEGRAM] TELEGRAM_SKIP_POLLING=true — skipping local bot polling.")
            logger.info("[TELEGRAM] Your Render server is handling Telegram. This is correct.")
            return None

        # Auto-detect: try getUpdates; if 409 Conflict, skip gracefully
        try:
            import httpx
            resp = httpx.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                timeout=5
            )
            data = resp.json()
            if not data.get("ok") and data.get("error_code") == 409:
                logger.warning(
                    "[TELEGRAM] Another bot instance is already running (Render server?). "
                    "Skipping local polling to avoid conflicts. "
                    "Set TELEGRAM_SKIP_POLLING=true in .env to silence this check."
                )
                return None
        except Exception:
            pass  # If the check itself fails, proceed normally
    # ────────────────────────────────────────────────────────────────────────

    application = ApplicationBuilder().token(token).build()
    application.bot_data["chat_service"] = chat_service
    application.bot_data["memory_service"] = getattr(chat_service, 'memory_service', None)
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("brief", brief_command))
    application.add_handler(CommandHandler("cal", cal_command))
    application.add_handler(CommandHandler("mail", mail_command))
    application.add_handler(CommandHandler("screen", screen_command))
    application.add_handler(CommandHandler("press", press_command))
    application.add_handler(CommandHandler("type", type_command))
    application.add_handler(CommandHandler("scroll", scroll_command))
    application.add_handler(CommandHandler("sendfile", sendfile_command))
    application.add_handler(CommandHandler("memory", memory_command))
    application.add_handler(CommandHandler("forget", forget_command))
    application.add_handler(CommandHandler("mode", mode_command))
    application.add_handler(CommandHandler("apply_fix", apply_fix_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    application.add_handler(MessageHandler(filters.PHOTO, photo_message))
    
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
