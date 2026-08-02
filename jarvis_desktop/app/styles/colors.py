# jarvis_desktop/app/styles/colors.py

"""
Color System for JARVIS Native Desktop UI
Sci-Fi HUD aesthetic — electric cyan primary, deep space background, purple active accent.
"""

# ── Base Background & Surface Colors ─────────────────────────────────────────
BG_COLOR = "#050510"
DEEP_BG = "#0A1628"                     # HUD: deep navy for scan-line layer
GLASS_BG = "rgba(10, 10, 28, 0.72)"
GLASS_BG_SOLID = "#0a0a1c"
GLASS_BORDER = "rgba(255, 255, 255, 0.06)"
GLASS_BORDER_HEX = "#1e1e36"
GLASS_HOVER = "rgba(255, 255, 255, 0.10)"

# ── HUD Cyan Accent Colors ────────────────────────────────────────────────────
CYAN_PRIMARY = "#00D9FF"                # Electric cyan — primary HUD accent
CYAN_GLOW = "#00FFF0"                   # Bright cyan — glow highlights/rings
CYAN_DIM = "rgba(0, 217, 255, 0.08)"   # Very dim cyan — subtle backgrounds
CYAN_BORDER = "rgba(0, 217, 255, 0.18)" # Thin glowing cyan border
CYAN_BORDER_BRIGHT = "rgba(0, 217, 255, 0.35)" # Hover/active cyan border
CYAN_GLOW_RGBA = "rgba(0, 217, 255, 0.25)" # Ambient glow

# ── Brand Accent Colors (Purple stays as CTA/active-state accent) ─────────────
ACCENT_PRIMARY = "#7c6aef"              # Purple — send button, active mode pill
ACCENT_GLOW = "rgba(124, 106, 239, 0.35)"
ACCENT_SECONDARY = "#4ecdc4"            # Teal (retained for gradient)
ACCENT_GRADIENT_START = "#7c6aef"
ACCENT_GRADIENT_END = "#4ecdc4"

# ── Typography & Text Colors ──────────────────────────────────────────────────
TEXT_PRIMARY = "#ffffff"
TEXT_MAIN = "rgba(255, 255, 255, 0.93)"
TEXT_DIM = "rgba(255, 255, 255, 0.50)"
TEXT_MUTED = "rgba(255, 255, 255, 0.28)"

# ── Status & Signal Colors ────────────────────────────────────────────────────
STATUS_ONLINE = "#51cf66"               # Green
STATUS_OFFLINE = "#ff6b6b"             # Red/Danger
STATUS_WARNING = "#fcc419"             # Amber/Yellow
STATUS_INFO = CYAN_PRIMARY             # Cyan (was blue #339af0)

# ── Chat & Message Container Colors ──────────────────────────────────────────
USER_BUBBLE_BG = "#2a1b4e"
USER_BUBBLE_BORDER = "#483285"
ASSISTANT_BUBBLE_BG = "rgba(10, 22, 40, 0.85)"
ASSISTANT_BUBBLE_BORDER = "rgba(0, 217, 255, 0.12)"

# ── Card & Control Colors ─────────────────────────────────────────────────────
CARD_BG = "rgba(10, 14, 30, 0.70)"
CARD_BORDER = "rgba(0, 217, 255, 0.12)"
INPUT_BG = "rgba(8, 8, 20, 0.85)"
INPUT_BORDER = "rgba(255, 255, 255, 0.10)"
INPUT_BORDER_FOCUS = CYAN_PRIMARY
