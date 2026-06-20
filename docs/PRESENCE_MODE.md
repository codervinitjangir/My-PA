# JARVIS Presence Mode (v1)

## Overview
**Presence Mode v1** is a dark glassmorphic, lightweight PySide6 companion window. It represents JARVIS on the desktop without adding "Agentic Bloat". 

## States & Interaction
The UI operates strictly across 5 states:
1. 🟢 **Active**
2. ⚙ **Processing** (When Briefing or Analyzing)
3. 🔴 **Offline** (Backend unreachable, buttons disabled, auto-polling suspended for 60s)
4. 🟡 **Wake Word Coming Soon**
5. 📴 **Hidden** (System Tray only)

**Mini Expand Mode**
- Single-click: Expands to `300x170` view showing Workspace, Pending, and Latency.
- Double-click: Collapses to a tiny `40x40` 🟢 J floating bubble.
- All states and $(x, y)$ positions are persisted locally.

## Actions
- **Talk**: Triggers a browser shortcut to `/?action=talk` (focusing the existing dashboard STT engine).
- **Brief**: Manually calls `/briefing`.
- **Analyze**: Manually POSTs screen context to `/operator/action`.
- **Dashboard**: Opens the local browser tab.
- **Wake Word**: Disabled placeholder for a future lightweight integration.

## Trust Evaluation Checklist
- [x] Does it steal focus? No.
- [x] Does it pop up randomly? No.
- [x] Does it duplicate AI logic? No.
- [x] Does it run background workers? No, just one UI QTimer.
- [x] Can Boss trust it? Yes, it is purely an API visualizer layer.
