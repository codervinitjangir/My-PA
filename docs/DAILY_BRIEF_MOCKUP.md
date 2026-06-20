# DAILY BRIEF MOCKUP

## Dedicated Briefing Panel

The Daily Brief acts as an exclusive popup panel (separated from the chat interface) designed to prepare the user for their immediate tasks. It changes content dynamically based on the current system state, pending workloads, and time of day.

```text
+-------------------------------------------------------------+
|                                                       [X]   |
|  Good Morning Boss. Here is your daily briefing.            |
|                                                             |
|  [ Today Mode ]                                             |
|  🚀 Build                                                   |
|                                                             |
|  [ Energy Score ]                                           |
|  High (Optimal conditions for deep work)                    |
|                                                             |
|  [ Today's Focus ]                                          |
|  Jarvis OS Refactoring                                      |
|                                                             |
|  [ Active Projects ]                                        |
|  - Jarvis Dashboard Implementation                          |
|  - Daily Briefing Engine                                    |
|                                                             |
|  [ Pending Tasks ]                                          |
|  3 items require your attention.                            |
|                                                             |
|  [ Computer Status ]                                        |
|  All systems nominal. CPU: 14%, RAM: 45%.                   |
|                                                             |
|  [ Suggested Action ]                                       |
|  Continue Jarvis -> [Execute Button]                        |
|                                                             |
+-------------------------------------------------------------+
```

### Time of Day Variations
- **Morning (05:00 - 11:59)**: "Good Morning Boss. Here is your daily briefing."
- **Afternoon (12:00 - 16:59)**: "Good Afternoon Boss. Here is your mid-day status."
- **Evening (17:00 - 04:59)**: "Good Evening Boss. Here is your end-of-day summary."

### Dynamic Today Modes
- `🚀 Build`: Triggered when "active_project" is present.
- `📚 Learn`: Triggered when focus contains "learn" or "research".
- `💼 Work`: Triggered when pending items > 5.
- `😴 Light Day`: Triggered when pending items == 0.

### Energy Score Logic
- `High`: CPU < 50% and RAM < 60%
- `Medium`: CPU < 80% and RAM < 85%
- `Low`: CPU >= 80% or RAM >= 85%
