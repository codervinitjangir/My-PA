# Web Assistant (v0.5)

The **Web Assistant** (formerly Guided Browser Awareness) is a strict, minimalist tool designed to reduce friction during web tasks without transforming JARVIS into an autonomous agent.

## Core Philosophy

- **Stateless Execution:** The Web Assistant does not hold persistent browser sessions. It executes single commands and immediately drops the context.
- **No Background Processes:** Open and Search functions use native OS browser hooks, guaranteeing 0% CPU footprint after execution.
- **Strictly Observable:** JARVIS does not click buttons, submit forms, or automate workflows behind the scenes.

## Allowed Commands

Only **3** capabilities are allowed in v0.5:

### 1. Open
Opens a specified URL safely in your native browser.
> "Jarvis open GitHub"
> "Jarvis open Gmail"

### 2. Search
Quickly launches a Google search in your native browser.
> "Jarvis search FastAPI docs"
> "Jarvis search backend internships"

### 3. Summarize URL
Retrieves the text from a specific URL using a lightweight Python request (no browser engine), strips out bloat, and provides a strict LLM summary.
> "Jarvis summarize https://fastapi.tiangolo.com"
> "Jarvis summarize https://github.com/openai/openai-python"

**Response Format:**
```
📄 Title
🎯 Main topic
• Point 1
• Point 2
• Point 3
• Point 4
• Point 5
```

## Security Layer

The Web Assistant is physically blocked at the `security_rules.py` layer from performing any autonomous tasks. If an LLM hallucinates a command to `click()`, `scroll()`, or `login()`, it will instantly trigger a `PermissionError`.

## Architecture Checklist

- Playwright installed? ❌ **No.** (Keeps footprint tiny)
- Persistent Browser? ❌ **No.**
- New Subsystem Managers? ❌ **No.**
- New Folders? ❌ **No.**
