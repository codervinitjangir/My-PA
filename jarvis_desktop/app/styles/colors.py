# jarvis_desktop/app/styles/colors.py

"""
Color System for JARVIS Native Desktop UI
Matches CSS design tokens from frontend/style.css 1:1
"""

# Base Background & Surface Colors
BG_COLOR = "#050510"
GLASS_BG = "rgba(10, 10, 28, 0.72)"
GLASS_BG_SOLID = "#0a0a1c"
GLASS_BORDER = "rgba(255, 255, 255, 0.06)"
GLASS_BORDER_HEX = "#1e1e36"
GLASS_HOVER = "rgba(255, 255, 255, 0.10)"

# Brand Accent Colors
ACCENT_PRIMARY = "#7c6aef"          # Main Purple Accent
ACCENT_GLOW = "rgba(124, 106, 239, 0.35)"
ACCENT_SECONDARY = "#4ecdc4"     # Cyan Accent
ACCENT_GRADIENT_START = "#7c6aef"
ACCENT_GRADIENT_END = "#4ecdc4"

# Typography & Text Colors
TEXT_PRIMARY = "#ffffff"
TEXT_MAIN = "rgba(255, 255, 255, 0.93)"
TEXT_DIM = "rgba(255, 255, 255, 0.50)"
TEXT_MUTED = "rgba(255, 255, 255, 0.28)"

# Status & Signal Colors
STATUS_ONLINE = "#51cf66"         # Green
STATUS_OFFLINE = "#ff6b6b"        # Red/Danger
STATUS_WARNING = "#fcc419"        # Amber/Yellow
STATUS_INFO = "#339af0"           # Blue

# Chat & Message Container Colors
USER_BUBBLE_BG = "#2a1b4e"
USER_BUBBLE_BORDER = "#483285"
ASSISTANT_BUBBLE_BG = "rgba(18, 18, 42, 0.85)"
ASSISTANT_BUBBLE_BORDER = "rgba(124, 106, 239, 0.18)"

# Card & Control Colors
CARD_BG = "rgba(15, 15, 36, 0.65)"
CARD_BORDER = "rgba(255, 255, 255, 0.08)"
INPUT_BG = "rgba(8, 8, 20, 0.85)"
INPUT_BORDER = "rgba(255, 255, 255, 0.12)"
INPUT_BORDER_FOCUS = "#7c6aef"
