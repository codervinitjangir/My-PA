import os
import time
import urllib.request
import urllib.parse
import json
import logging

logger = logging.getLogger(__name__)

TELEGRAM_COOLDOWN = 2
_last_request_time = {}

def is_allowed_user(user_id: int) -> bool:
    allowed_ids = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
    if not allowed_ids:
        return False
    return str(user_id) in [x.strip() for x in allowed_ids.split(',')]

def send_telegram_message(chat_id: int, text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.warning("[TELEGRAM] Cannot send message: Token not set.")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            pass
    except Exception as e:
        logger.error(f"[TELEGRAM] Failed to send message: {e}")

def handle_telegram_command(chat_id: int, user_id: int, text: str) -> None:
    if not is_allowed_user(user_id):
        logger.warning(f"[TELEGRAM] Unauthorized access attempt by {user_id}")
        return

    now = time.time()
    last = _last_request_time.get(user_id, 0)
    if now - last < TELEGRAM_COOLDOWN:
        logger.info(f"[TELEGRAM] Rate limited user {user_id}")
        return
    _last_request_time[user_id] = now

    command = text.strip().lower()
    
    if command == "/status":
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/mobile/state")
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
            msg = f"🟢 Current Status\n\n"
            msg += f"Focus: {data.get('current_focus', 'None')}\n"
            msg += f"Project: {data.get('current_project', 'None')}\n"
            msg += f"Pending Tasks: {data.get('pending_count', 0)}\n"
            msg += f"Workspace: {data.get('workspace', 'Jarvis')}"
            send_telegram_message(chat_id, msg)
        except Exception as e:
            send_telegram_message(chat_id, f"Error getting status: {e}")

    elif command == "/dashboard":
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/mobile/state")
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
            send_telegram_message(chat_id, f"Dashboard: {data.get('greeting', 'Hello')}")
        except Exception:
            send_telegram_message(chat_id, "Dashboard unavailable.")

    elif command in ("/brief", "/resume"):
        action = "morning_brief" if command == "/brief" else "resume_session"
        try:
            payload = json.dumps({"action": action}).encode('utf-8')
            req = urllib.request.Request("http://127.0.0.1:8000/operator/action", data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as response:
                pass
            send_telegram_message(chat_id, f"{command.title().strip('/')} triggered on PC.")
        except Exception as e:
            send_telegram_message(chat_id, f"Failed: {e}")

    elif command == "/screen":
        send_telegram_message(chat_id, "Analyzing screen... please wait.")
        try:
            payload = json.dumps({"action": "analyze_screen"}).encode('utf-8')
            req = urllib.request.Request("http://127.0.0.1:8000/operator/action", data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
            if data.get("cooldown"):
                send_telegram_message(chat_id, f"Error: {data.get('error')}")
            else:
                send_telegram_message(chat_id, f"Screen Analysis:\n\n{data.get('summary', 'Unknown')}\n\nActivity: {data.get('activity', 'Unknown')}")
        except Exception as e:
            send_telegram_message(chat_id, f"Failed to analyze screen: {e}")

    elif command in ("/github", "/linkedin", "/chatgpt", "/leetcode", "/notion"):
        alias = command.replace("/", "")
        try:
            payload = json.dumps({"action": "open_site", "payload": {"site": alias}}).encode('utf-8')
            req = urllib.request.Request("http://127.0.0.1:8000/operator/action", data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as response:
                pass
            send_telegram_message(chat_id, f"Opened {alias} on PC.")
        except Exception:
            send_telegram_message(chat_id, f"Failed to open {alias}.")

    elif command == "/help":
        msg = (
            "Available commands:\n"
            "/status\n"
            "/dashboard\n"
            "/brief\n"
            "/resume\n"
            "/screen\n"
            "/github\n"
            "/linkedin\n"
            "/chatgpt\n"
            "/leetcode\n"
            "/notion"
        )
        send_telegram_message(chat_id, msg)
    else:
        send_telegram_message(chat_id, "Unknown command. Use /help")
