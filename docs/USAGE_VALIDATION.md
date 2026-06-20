# Usage Validation

Built during **Stabilization Sprint 2**.

This is NOT analytics. This is a mirror — it shows Boss exactly which parts of JARVIS are actually being used every day.

---

## What Is Tracked

| Event Key | Triggered When |
|---|---|
| `dashboard_open` | `GET /dashboard` is called |
| `morning_brief` | `GET /briefing` is called |
| `browser_open` | Any `open_site` action executes |
| `screen_analysis` | Screen analysis endpoint fires (Capability 1) |
| `session_resume` | Session resume action executes |
| `quick_links[site]` | A specific site alias is opened |

Only **meaningful actions** are tracked. Button hover, cursor moves, and page scrolls are not.

---

## Architecture

No new folders. No new managers.

| File | Role |
|---|---|
| `jarvis_os/core/usage.py` | 5 functions, ~95 lines |
| `jarvis_os/core/usage_log.json` | Single flat JSON file |
| `app/main.py` | `GET /usage` endpoint + 3 hook points |
| `frontend/components/dashboard.js` | `loadUsage()` + `renderUsage()` |
| `frontend/style.css` | Usage card styles |

---

## Usage Score

| Score | Condition |
|---|---|
| 🟢 High | > 10 total events today |
| 🟡 Medium | 5–10 total events |
| 🔴 Low | < 5 total events |

---

## API

`GET /usage` — returns `{ date, features, sites, total, score, score_label, most_used, least_used }`.

No POST. No auth. Read-only.

---

## After 7 Days

Read `usage_log.json`. If a feature shows 0 or near-zero across the week:

1. Log it as a friction item.
2. Decide: improve it or delete it.

That is the only purpose of this system.
