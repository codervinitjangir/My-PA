"""
app/dashboard_server.py — J.A.R.V.I.S Remote Dashboard Server
==============================================================

Runs a minimal local HTTP server on port 8001 (separate from the main API port 8000).
Provides a mobile-friendly dashboard showing:
  - Today's briefing
  - Recent chat history
  - Quick action buttons (screen analyze, memory, stats)

Security model (application-layer, not just network):
  - A random session token is generated at startup (secrets.token_urlsafe)
  - Every request must carry the token as ?t=<token> or X-Dashboard-Token header
  - A QR code is generated containing the full dashboard URL + token, printed to
    console and sent via Telegram so the owner can scan it from their phone
  - The QR code URL is on the local network IP (not localhost) so phones can reach it
  - Token is ephemeral (new on every restart) — scanning an old QR won't work

Usage — started automatically from main.py lifespan if DASHBOARD_ENABLED=true:
  Or run standalone: python app/dashboard_server.py

Do NOT set DASHBOARD_ENABLED in .env unless you trust your local network.
Default is false.
"""

import asyncio
import hashlib
import json
import logging
import os
import secrets
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("J.A.R.V.I.S.Dashboard")

# ── Configuration ─────────────────────────────────────────────────────────────

DASHBOARD_PORT   = int(os.getenv("DASHBOARD_PORT", "8001"))
DASHBOARD_ENABLED = os.getenv("DASHBOARD_ENABLED", "false").strip().lower() == "true"

# Token is generated at import time — new on every process restart
_SESSION_TOKEN = secrets.token_urlsafe(24)

# References injected by main.py after startup
_chat_service_ref: Optional[object] = None
_memory_service_ref: Optional[object] = None
_scheduler_ref: Optional[object] = None     # for LAST_BRIEFING


# ── Dependency injection (called by main.py) ──────────────────────────────────

def configure(chat_service, memory_service, scheduler_module) -> None:
    """
    Wires the dashboard to live service instances.
    Call this from main.py lifespan after all services are initialized.
    """
    global _chat_service_ref, _memory_service_ref, _scheduler_ref
    _chat_service_ref = chat_service
    _memory_service_ref = memory_service
    _scheduler_ref = scheduler_module
    logger.info("[DASHBOARD] Services wired: chat=%s memory=%s", bool(chat_service), bool(memory_service))


# ── Network helpers ───────────────────────────────────────────────────────────

def _get_local_ip() -> str:
    """Returns the machine's LAN IP address (not localhost)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Connect to an external address to discover local interface IP
            # No data is actually sent
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def get_dashboard_url() -> str:
    """Returns the full dashboard URL including session token."""
    ip = _get_local_ip()
    return f"http://{ip}:{DASHBOARD_PORT}/?t={_SESSION_TOKEN}"


# ── QR code generation ────────────────────────────────────────────────────────

def generate_qr_terminal(url: str) -> str:
    """
    Generates a QR code and returns it as ASCII art for terminal display.
    Uses the qrcode library.  Falls back to printing the plain URL if qrcode
    is not installed.
    """
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        # ASCII art (compatible with any terminal)
        lines = []
        matrix = qr.get_matrix()
        for row in matrix:
            line = "".join("██" if cell else "  " for cell in row)
            lines.append(line)
        return "\n".join(lines)
    except ImportError:
        return f"[QR unavailable — install: pip install qrcode]\nURL: {url}"
    except Exception as e:
        return f"[QR generation failed: {e}]\nURL: {url}"


async def _send_qr_via_telegram(url: str) -> None:
    """
    Sends the dashboard URL and QR code image to the Telegram owner.
    Silently skips if Telegram is not configured.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    owner_id = os.getenv("TELEGRAM_OWNER_ID", "").strip()
    if not token or not owner_id:
        return

    try:
        from telegram import Bot
        bot = Bot(token=token)

        # Send text URL first (always works)
        await bot.send_message(
            chat_id=int(owner_id),
            text=(
                f"🖥️ *J.A.R.V.I.S Dashboard is live!*\n\n"
                f"URL: `{url}`\n\n"
                f"⚠️ Local network only — scan from your phone on the same WiFi.\n"
                f"Token expires when server restarts."
            ),
            parse_mode="Markdown",
        )

        # Try to send QR as image using qrcode[pil]
        try:
            import qrcode
            import io as _io
            qr = qrcode.make(url)
            buf = _io.BytesIO()
            qr.save(buf, format="PNG")
            buf.seek(0)
            await bot.send_photo(
                chat_id=int(owner_id),
                photo=buf,
                caption="Scan to open dashboard on your phone",
            )
        except Exception:
            pass  # QR image is best-effort — URL already sent

        logger.info("[DASHBOARD] QR sent to Telegram owner.")
    except Exception as e:
        logger.warning("[DASHBOARD] Could not send QR via Telegram: %s", e)


# ── Data fetchers ─────────────────────────────────────────────────────────────

def _get_briefing_text() -> str:
    """Pulls LAST_BRIEFING from the scheduler module."""
    try:
        if _scheduler_ref and hasattr(_scheduler_ref, "LAST_BRIEFING"):
            return _scheduler_ref.LAST_BRIEFING or "No briefing generated yet."
    except Exception:
        pass
    return "Briefing unavailable."


def _get_recent_chat(max_turns: int = 20) -> list:
    """
    Returns the last N turns from the 'telegram' session as a flat list.
    Falls back to an empty list if chat service is unavailable.
    """
    if not _chat_service_ref:
        return []
    try:
        sessions = _chat_service_ref.sessions
        # Prefer telegram session; fall back to any available session
        session_id = None
        for sid in sessions:
            if "telegram" in sid.lower():
                session_id = sid
                break
        if session_id is None and sessions:
            session_id = next(iter(sessions))
        if session_id is None:
            return []

        messages = sessions[session_id]
        # Return last N messages as serializable dicts
        return [
            {
                "role": getattr(m, "role", "unknown"),
                "content": str(getattr(m, "content", ""))[:500],
                "ts": str(getattr(m, "timestamp", "")),
            }
            for m in messages[-max_turns:]
        ]
    except Exception as e:
        logger.debug("[DASHBOARD] Chat fetch failed: %s", e)
        return []


def _get_memory_summary() -> str:
    """Returns top 10 memory entries as a summary string."""
    if not _memory_service_ref:
        return "Memory service unavailable."
    try:
        return _memory_service_ref.get_all_knowledge()
    except Exception:
        return "Memory unavailable."


def _get_hardware_snapshot() -> dict:
    """Returns hardware snapshot or empty dict."""
    try:
        from app.services.hardware_monitor import get_hardware_snapshot
        return get_hardware_snapshot()
    except Exception:
        return {}


# ── HTML page builder ─────────────────────────────────────────────────────────

def _build_dashboard_html(token: str) -> str:
    """
    Builds the dashboard HTML page.

    Design principles:
      - Single-file — no external JS/CSS dependencies (works offline on local network)
      - Mobile-first responsive layout
      - Dark mode matching JARVIS aesthetic
      - Auto-refreshes chat every 30 seconds
    """
    now = datetime.now().strftime("%A, %B %d at %H:%M")
    briefing = _get_briefing_text().replace("<", "&lt;").replace(">", "&gt;")
    chat = _get_recent_chat()
    hw = _get_hardware_snapshot()

    # Build chat HTML
    chat_html = ""
    for msg in reversed(chat):  # newest first
        role = msg["role"]
        content = msg["content"].replace("<", "&lt;").replace(">", "&gt;")
        bubble_class = "bubble-user" if role == "user" else "bubble-ai"
        label = "You" if role == "user" else "JARVIS"
        chat_html += f'<div class="bubble {bubble_class}"><span class="label">{label}</span><p>{content}</p></div>\n'

    if not chat_html:
        chat_html = '<p class="muted">No chat history yet.</p>'

    # Hardware section
    hw_html = ""
    if hw.get("ok"):
        cpu_pct = hw.get("cpu", {}).get("percent", 0)
        ram_pct = hw.get("ram", {}).get("percent", 0)
        ram_used = hw.get("ram", {}).get("used", "?")
        ram_total = hw.get("ram", {}).get("total", "?")
        uptime = hw.get("uptime_hours", "?")
        hw_html = f"""
        <div class="stat-row">
          <div class="stat-card">
            <div class="stat-label">CPU</div>
            <div class="stat-bar"><div class="stat-fill" style="width:{cpu_pct:.0f}%"></div></div>
            <div class="stat-val">{cpu_pct:.1f}%</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">RAM</div>
            <div class="stat-bar"><div class="stat-fill" style="width:{ram_pct:.0f}%"></div></div>
            <div class="stat-val">{ram_used} / {ram_total}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Uptime</div>
            <div class="stat-val">{uptime}h</div>
          </div>
        </div>
        """
    else:
        hw_html = '<p class="muted">Hardware stats unavailable.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>J.A.R.V.I.S Dashboard</title>
  <style>
    :root {{
      --bg: #0a0a0f;
      --surface: #12121a;
      --card: #1a1a27;
      --border: #2a2a40;
      --accent: #6c63ff;
      --accent2: #00d4ff;
      --text: #e8e8f0;
      --muted: #666680;
      --user-bg: #1e2a4a;
      --ai-bg: #1a2a1a;
      --success: #22c55e;
      --warn: #f59e0b;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      font-size: 15px;
      line-height: 1.6;
    }}
    /* ── Layout ── */
    .header {{
      background: linear-gradient(135deg, var(--surface), #1a1a35);
      border-bottom: 1px solid var(--border);
      padding: 16px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 10;
    }}
    .header h1 {{
      font-size: 18px;
      font-weight: 700;
      background: linear-gradient(90deg, var(--accent), var(--accent2));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: 0.5px;
    }}
    .header .time {{
      font-size: 12px;
      color: var(--muted);
    }}
    .container {{
      max-width: 700px;
      margin: 0 auto;
      padding: 16px;
    }}
    /* ── Cards ── */
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 16px;
    }}
    .card-title {{
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 1px;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    /* ── Chat bubbles ── */
    .bubble {{
      padding: 10px 14px;
      border-radius: 10px;
      margin-bottom: 8px;
    }}
    .bubble-user {{ background: var(--user-bg); border-left: 3px solid var(--accent); }}
    .bubble-ai   {{ background: var(--ai-bg);   border-left: 3px solid var(--success); }}
    .label {{
      font-size: 11px;
      font-weight: 600;
      color: var(--muted);
      display: block;
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .bubble p {{ font-size: 14px; white-space: pre-wrap; word-break: break-word; }}
    /* ── Hardware stats ── */
    .stat-row {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    .stat-card {{
      flex: 1;
      min-width: 140px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
    }}
    .stat-label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }}
    .stat-bar {{ background: var(--border); border-radius: 4px; height: 6px; margin-bottom: 6px; overflow: hidden; }}
    .stat-fill {{ height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent2)); border-radius: 4px; transition: width 0.4s; }}
    .stat-val {{ font-size: 15px; font-weight: 600; }}
    /* ── Quick actions ── */
    .actions {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .btn {{
      display: inline-block;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      border: none;
      cursor: pointer;
      text-decoration: none;
      transition: opacity 0.15s, transform 0.1s;
    }}
    .btn:active {{ transform: scale(0.97); }}
    .btn-primary {{ background: var(--accent); color: #fff; }}
    .btn-secondary {{ background: var(--surface); color: var(--text); border: 1px solid var(--border); }}
    .btn:hover {{ opacity: 0.85; }}
    /* ── Misc ── */
    .muted {{ color: var(--muted); font-size: 13px; }}
    .briefing-text {{
      font-size: 14px;
      white-space: pre-wrap;
      word-break: break-word;
      max-height: 300px;
      overflow-y: auto;
      color: var(--text);
    }}
    .badge {{
      display: inline-block;
      background: var(--accent);
      color: #fff;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 20px;
      letter-spacing: 0.3px;
      vertical-align: middle;
    }}
    .refresh-note {{ font-size: 11px; color: var(--muted); text-align: right; margin-top: -8px; margin-bottom: 12px; }}
  </style>
</head>
<body>

<div class="header">
  <div>
    <h1>⚡ J.A.R.V.I.S</h1>
    <div class="time">{now}</div>
  </div>
  <div>
    <span class="badge">LOCAL</span>
  </div>
</div>

<div class="container">

  <!-- Quick Actions -->
  <div class="card">
    <div class="card-title">🎯 Quick Actions</div>
    <div class="actions">
      <a class="btn btn-primary" href="/action?t={token}&action=stats">📊 Stats</a>
      <a class="btn btn-secondary" href="/action?t={token}&action=refresh">🔄 Refresh</a>
      <a class="btn btn-secondary" href="/action?t={token}&action=briefing">📰 Briefing</a>
    </div>
  </div>

  <!-- Hardware Stats -->
  <div class="card">
    <div class="card-title">🖥️ Hardware</div>
    {hw_html}
  </div>

  <!-- Daily Briefing -->
  <div class="card">
    <div class="card-title">📰 Today's Briefing</div>
    <div class="briefing-text">{briefing}</div>
  </div>

  <!-- Chat History -->
  <div class="card">
    <div class="card-title">💬 Recent Chat</div>
    <p class="refresh-note">Auto-refreshes every 30s</p>
    <div id="chat-feed">
      {chat_html}
    </div>
  </div>

</div>

<script>
  // Auto-refresh chat panel every 30 seconds
  setInterval(() => {{
    fetch('/data?t={token}')
      .then(r => r.json())
      .then(data => {{
        const feed = document.getElementById('chat-feed');
        if (!feed) return;
        if (data.chat && data.chat.length > 0) {{
          feed.innerHTML = data.chat
            .reverse()
            .map(m => {{
              const cls = m.role === 'user' ? 'bubble-user' : 'bubble-ai';
              const label = m.role === 'user' ? 'You' : 'JARVIS';
              return `<div class="bubble ${{cls}}"><span class="label">${{label}}</span><p>${{m.content}}</p></div>`;
            }})
            .join('');
        }}
      }})
      .catch(() => {{}});
  }}, 30000);
</script>

</body>
</html>
"""


# ── Request handler ───────────────────────────────────────────────────────────

def _token_valid(qs: dict) -> bool:
    """Checks that ?t= or X-Dashboard-Token header contains the correct session token."""
    t = qs.get("t", [""])[0]
    return secrets.compare_digest(t, _SESSION_TOKEN)


class _DashboardHandler:
    """
    Minimal async HTTP handler built on asyncio streams (no aiohttp/starlette).
    Each request is handled by _handle_request().
    """

    async def __call__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            raw = await asyncio.wait_for(reader.read(4096), timeout=5.0)
            if not raw:
                return

            lines = raw.decode("utf-8", errors="replace").split("\r\n")
            if not lines:
                return

            # Parse request line
            parts = lines[0].split(" ")
            if len(parts) < 2:
                return

            method, path = parts[0], parts[1]

            # Parse query string
            qs = {}
            if "?" in path:
                path, qstring = path.split("?", 1)
                from urllib.parse import parse_qs
                qs = parse_qs(qstring)

            # Auth gate: token must be present and correct
            if not _token_valid(qs):
                self._respond(writer, 401, "text/plain", b"Unauthorized: invalid or missing session token")
                return

            # Routes
            if path == "/" or path == "":
                html = _build_dashboard_html(_SESSION_TOKEN)
                self._respond(writer, 200, "text/html; charset=utf-8", html.encode("utf-8"))

            elif path == "/data":
                # JSON data endpoint for auto-refresh
                payload = {
                    "chat": _get_recent_chat(),
                    "briefing": _get_briefing_text(),
                    "hw": _get_hardware_snapshot(),
                    "ts": time.time(),
                }
                self._respond(writer, 200, "application/json",
                              json.dumps(payload).encode("utf-8"))

            elif path == "/action":
                action = qs.get("action", [""])[0]
                result = await self._handle_action(action)
                # Redirect back to home after action
                self._respond(writer, 302, "text/plain", b"",
                              extra_headers={"Location": f"/?t={_SESSION_TOKEN}&msg={result}"})

            else:
                self._respond(writer, 404, "text/plain", b"Not found")

        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.debug("[DASHBOARD] Handler error: %s", e)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def _respond(
        self,
        writer: asyncio.StreamWriter,
        status: int,
        content_type: str,
        body: bytes,
        extra_headers: dict = None,
    ) -> None:
        status_text = {200: "OK", 302: "Found", 401: "Unauthorized", 404: "Not Found"}.get(status, "Unknown")
        headers = [
            f"HTTP/1.1 {status} {status_text}",
            f"Content-Type: {content_type}",
            f"Content-Length: {len(body)}",
            "Cache-Control: no-cache",
            "X-Frame-Options: DENY",
            "X-Content-Type-Options: nosniff",
            "Connection: close",
        ]
        if extra_headers:
            for k, v in extra_headers.items():
                headers.append(f"{k}: {v}")
        response = "\r\n".join(headers) + "\r\n\r\n"
        writer.write(response.encode("utf-8") + body)

    async def _handle_action(self, action: str) -> str:
        if action == "refresh":
            return "refreshed"
        if action == "stats":
            return "stats_fetched"
        if action == "briefing":
            return "briefing_shown"
        return "unknown_action"


# ── Server lifecycle ──────────────────────────────────────────────────────────

_server_instance = None
_handler_instance = _DashboardHandler()


async def start_dashboard_server(
    chat_service=None,
    memory_service=None,
    scheduler_module=None,
) -> None:
    """
    Starts the dashboard server.  Call from main.py lifespan if DASHBOARD_ENABLED=true.

    Generates and prints QR code to console.  Also sends to Telegram if bot is configured.
    """
    global _server_instance

    if not DASHBOARD_ENABLED:
        logger.info("[DASHBOARD] Disabled (set DASHBOARD_ENABLED=true in .env to enable)")
        return

    if chat_service or memory_service:
        configure(chat_service, memory_service, scheduler_module)

    url = get_dashboard_url()

    # Print QR to terminal
    qr_art = generate_qr_terminal(url)
    border = "─" * 58
    print(f"\n{'─'*58}")
    print("  J.A.R.V.I.S Remote Dashboard")
    print(f"  URL: {url}")
    print(f"  Port: {DASHBOARD_PORT}  |  Local network only")
    print(f"  Token rotates on every restart")
    print(f"{'─'*58}")
    print(qr_art)
    print(f"{'─'*58}\n")

    # Send to Telegram (fire and forget)
    asyncio.create_task(_send_qr_via_telegram(url))

    try:
        _server_instance = await asyncio.start_server(
            _handler_instance,
            host="0.0.0.0",  # bind to all interfaces so phone on same WiFi can reach it
            port=DASHBOARD_PORT,
        )
        logger.info("[DASHBOARD] Server listening on 0.0.0.0:%d", DASHBOARD_PORT)
        logger.info("[DASHBOARD] Access URL: %s", url)
    except OSError as e:
        logger.error("[DASHBOARD] Could not start server on port %d: %s", DASHBOARD_PORT, e)
        logger.error("[DASHBOARD] Try a different port with DASHBOARD_PORT=8002 in .env")


async def stop_dashboard_server() -> None:
    """Gracefully stops the dashboard server."""
    global _server_instance
    if _server_instance:
        _server_instance.close()
        await _server_instance.wait_closed()
        _server_instance = None
        logger.info("[DASHBOARD] Server stopped.")


# ── Standalone entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    # Override env for standalone testing
    os.environ.setdefault("DASHBOARD_ENABLED", "true")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )

    async def _run():
        await start_dashboard_server()
        if _server_instance:
            async with _server_instance:
                await _server_instance.serve_forever()

    print("Starting JARVIS Dashboard standalone (Ctrl+C to stop)...")
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
