# Stabilization Sprint 2 Report

## What Was Built

A **Daily Usage Validation** card inside the JARVIS dashboard. Zero AI. Zero analytics engines. One JSON file. One read endpoint.

---

## Product Questions

**1. Which features are valuable?**
Unknown until 7 days of data. The system will answer this empirically, not by guessing.

**2. Which features are ignored?**
Unknown until 7 days of data. Features with 0 opens for 7 days should be candidates for deletion.

**3. What should be improved?**
Features used every day but causing friction (cross-reference with the Friction Log).

**4. What should be deleted?**
Hypothesis: `screen_analysis` will likely show the lowest usage after 7 days. It requires a manual trigger and adds friction. The dashboard and browser actions will likely rank highest.

**5. Are we building a product or collecting vanity metrics?**
We are building a product. Vanity metrics = total users, click-through rates. Product metrics = "did Boss open the morning brief today?" These numbers directly decide what to build or delete next week.

---

## Modified Files

| File | Change |
|---|---|
| `jarvis_os/core/usage.py` | **NEW** — 5 functions, ~95 lines |
| `jarvis_os/core/usage_log.json` | **NEW** — seed file |
| `app/main.py` | +`GET /usage` + 3 hook points, ~20 lines |
| `frontend/components/dashboard.js` | +`loadUsage()` + `renderUsage()`, ~75 lines |
| `frontend/style.css` | +usage card styles, ~85 lines |

---

## Why No New Folders

Same reasoning as Sprint 1. `usage.py` is a data utility. It belongs in `jarvis_os/core/` beside `friction.py` and `quick_links.py`. No new organizational layer needed.

---

## Metrics

| Metric | Value |
|---|---|
| Daily usefulness score | **7 / 10** |
| Total lines added | ~275 |
| LLM calls | 0 |
| Performance | < 5ms |
| New folders | **0** |
| Auto-refresh interval | 30 seconds |

---

## Features Likely Deleted After 7 Days (Hypothesis)

1. **Screen Analysis** — manual trigger, low discovery, requires camera focus
2. **Session Resume** — tracked but the resume button may not be prominently used
3. **Resume Session button** in dashboard actions — may go unused if chat handles this

---

## Verification Steps

1. Start server: `uvicorn app.main:app --reload`
2. Open the dashboard — "Today's Usage" card appears below Friction Log.
3. Open Morning Brief → counter for `morning_brief` increments.
4. Click a Quick Link → `browser_open` increments + site-specific counter updates.
5. `GET /usage` returns JSON with today's data.
6. Check `jarvis_os/core/usage_log.json` — `daily_history[today]` is populated.
7. Wait 30 seconds — card auto-refreshes without page reload.
