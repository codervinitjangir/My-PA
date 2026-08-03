"""
ProactiveEngine — sends unprompted Telegram messages after extended silence.

Improvements over v1 (inspired by Mark-L's proactive.py):
  1. time.monotonic()     — drift-proof; unaffected by system clock adjustments
                            or NTP corrections that could fire or suppress triggers.
  2. Time-of-day context  — morning / afternoon / evening / late-night label
                            is injected into the prompt so the LLM can tailor
                            its tone (energetic morning vs. wind-down evening).
  3. STAY_SILENT signal   — the LLM can explicitly choose silence by responding
                            with exactly "STAY_SILENT". This prevents forced,
                            hollow messages when the LLM has nothing genuine to say.
  4. Decoupled mark_triggered() — the caller (scheduler.proactive_check) calls
                            mark_triggered() only AFTER a message is successfully
                            delivered. Previously this was buried inside
                            generate_proactive_message(), which meant a delivery
                            failure after generation would still consume the cooldown.

Wired into scheduler.py via a 5-minute APScheduler interval job.
"""

import time
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("J.A.R.V.I.S.Proactive")

# ── Thresholds (seconds) ────────────────────────────────────────────────────────
SILENCE_THRESHOLD_SEC = 15 * 60   # 15 minutes of user silence before we consider speaking
COOLDOWN_SEC          = 20 * 60   # minimum gap between consecutive proactive messages

# The LLM returns this exact token to opt out of speaking
_SILENT_SIGNAL = "STAY_SILENT"


def _get_time_of_day() -> str:
    """Returns a human label for the current time slot."""
    hour = datetime.now().hour
    if   6  <= hour < 12: return "morning"
    elif 12 <= hour < 18: return "afternoon"
    elif 18 <= hour < 23: return "evening"
    else:                  return "late night"


class ProactiveEngine:
    """
    Decides when and what to send as an unprompted message to the owner.

    Rotation modes (cycles via trigger_count % 3):
      0 — Recent conversation context: offers a natural follow-up from last chat
      1 — Active project mentions: pulls project knowledge from memory
      2 — Monitored/interesting topics: surfaces knowledge-base entries
          (falls back to mode 0 if no relevant data exists)
    """

    def __init__(self):
        # Use monotonic clock internally — immune to clock adjustments, NTP steps, etc.
        self._last_trigger_mono: float = 0.0   # monotonic time of last successful send
        self.trigger_count: int = 0             # rotates focus areas (% 3)

    # ── Gate ─────────────────────────────────────────────────────────────────────

    def should_trigger(self, last_user_message_time: Optional[float]) -> bool:
        """
        Returns True only when:
          * The user has been silent for 15+ minutes  (wall-clock delta), AND
          * At least 20 minutes have passed since our last proactive message
            (monotonic clock, unaffected by system time changes).

        If last_user_message_time is None (user never messaged), we never trigger.
        """
        if last_user_message_time is None:
            return False

        now_wall = time.time()
        now_mono = time.monotonic()

        # User silence uses wall clock (last_user_message_time is a wall-clock stamp)
        user_silent_for = now_wall - last_user_message_time
        if user_silent_for < SILENCE_THRESHOLD_SEC:
            return False

        # Cooldown uses monotonic clock (self._last_trigger_mono is monotonic)
        if self._last_trigger_mono > 0:
            cooldown_elapsed = now_mono - self._last_trigger_mono
            if cooldown_elapsed < COOLDOWN_SEC:
                return False

        return True

    def mark_triggered(self) -> None:
        """
        Records that a proactive message was successfully delivered.
        Must be called by the scheduler AFTER successful Telegram send —
        NOT inside generate_proactive_message() — so a failed delivery
        does not consume the cooldown window.
        """
        self._last_trigger_mono = time.monotonic()
        self.trigger_count += 1
        logger.info(
            "[PROACTIVE] Trigger #%d recorded (next allowed in %d min).",
            self.trigger_count,
            COOLDOWN_SEC // 60,
        )

    # ── Prompt builder ────────────────────────────────────────────────────────────

    def build_prompt(self, chat_service, session_id: str, memory_service) -> str:
        """
        Rotates through 3 focus areas (trigger_count % 3):
          Mode 0 — Recent conversation context
          Mode 1 — Active project mentions from memory
          Mode 2 — Monitored/interesting topics from knowledge base
        Falls back to mode 0 if the chosen mode has no usable data.
        """
        period = _get_time_of_day()
        mode   = self.trigger_count % 3

        # ── Base persona (time-of-day injected) ──────────────────────────────
        base_persona = (
            f"You are J.A.R.V.I.S., the AI assistant. It is {period}. "
            "Your owner hasn't messaged in a while. "
            "Send them a single, natural, helpful unprompted message — "
            "like a thoughtful assistant checking in or surfacing something genuinely useful. "
            "Be concise (1-3 sentences max). "
            "Never say 'I noticed you haven't messaged' or make the silence obvious. "
            "Sound natural and warm, never robotic or salesy.\n\n"
            # Escape hatch: LLM may decide silence is the better choice
            f"CRITICAL RULE: If nothing genuinely useful comes to mind for this {period}, "
            f"respond with exactly this token and nothing else: {_SILENT_SIGNAL}\n\n"
        )

        if mode == 1:
            prompt = self._build_project_prompt(base_persona, memory_service, period)
            if prompt:
                return prompt
            mode = 0   # fallback

        if mode == 2:
            prompt = self._build_topic_prompt(base_persona, memory_service, period)
            if prompt:
                return prompt
            mode = 0   # fallback

        # mode 0 (also fallback for 1 and 2)
        return self._build_context_prompt(base_persona, chat_service, session_id, period)

    def _build_context_prompt(
        self,
        base: str,
        chat_service,
        session_id: str,
        period: str,
    ) -> str:
        """Mode 0: natural follow-up from recent conversation history."""
        context_snippet = ""
        try:
            messages = chat_service.sessions.get(session_id, [])
            recent = [
                f"{m.role}: {m.content[:120]}"
                for m in messages[-8:]
                if getattr(m, "role", "") in ("user", "assistant")
            ]
            if recent:
                context_snippet = (
                    "Recent conversation (for context only — do NOT quote directly):\n"
                    + "\n".join(recent)
                    + "\n\n"
                )
        except Exception as e:
            logger.debug("[PROACTIVE] Could not read session history: %s", e)

        period_hints = {
            "morning":    "A morning check-in, a timely reminder, or an energising insight works well.",
            "afternoon":  "A mid-day nudge, a useful tip, or a progress check-in fits this time of day.",
            "evening":    "A gentle wind-down reminder, reflection, or something relaxing works well.",
            "late night": "Keep it brief and calm — they may be tired. A simple, caring note is enough.",
        }
        period_hint = period_hints.get(period, "")

        return (
            base
            + context_snippet
            + "Offer a natural, helpful follow-up thought, reminder, or useful insight "
            "that flows from the recent conversation. "
            + period_hint
            + " If no clear context, offer something generally useful for a busy person."
        )

    def _build_project_prompt(
        self,
        base: str,
        memory_service,
        period: str,
    ) -> Optional[str]:
        """Mode 1: actionable tip related to the user's active projects."""
        try:
            with memory_service._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT content FROM knowledge WHERE category = 'project' "
                    "ORDER BY updated_at DESC LIMIT 3"
                )
                rows = cursor.fetchall()

            if not rows:
                return None

            projects = "\n".join(f"- {row[0]}" for row in rows)
            period_hints = {
                "morning":    "A morning suggestion to make progress on one of these is ideal.",
                "afternoon":  "A specific next step or mid-project check fits the afternoon energy.",
                "evening":    "A gentle reminder or reflection on what was accomplished today.",
                "late night": "Keep it brief. A single encouraging observation is enough.",
            }
            period_hint = period_hints.get(period, "")

            return (
                base
                + f"Active projects the owner is working on:\n{projects}\n\n"
                + "Offer a genuinely useful tip, reminder, or next-step suggestion "
                "related to one of these projects. Be specific and actionable. "
                + period_hint
            )
        except Exception as e:
            logger.debug("[PROACTIVE] Could not read project knowledge: %s", e)
            return None

    def _build_topic_prompt(
        self,
        base: str,
        memory_service,
        period: str,
    ) -> Optional[str]:
        """Mode 2: surfaces interesting facts/decisions from the knowledge base."""
        try:
            with memory_service._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT content FROM knowledge "
                    "WHERE category IN ('decision', 'fact', 'resource') "
                    "ORDER BY updated_at DESC LIMIT 3"
                )
                rows = cursor.fetchall()

            if not rows:
                return None

            topics = "\n".join(f"- {row[0]}" for row in rows)
            return (
                base
                + f"Interesting things from the owner's knowledge base:\n{topics}\n\n"
                + "Reference ONE of these topics in a helpful, natural way — "
                "perhaps connecting it to something timely or actionable this "
                + period + "."
            )
        except Exception as e:
            logger.debug("[PROACTIVE] Could not read knowledge topics: %s", e)
            return None

    # ── Message generator ─────────────────────────────────────────────────────────

    def generate_proactive_message(
        self,
        llm_router,
        chat_service,
        session_id: str,
        memory_service,
    ) -> Optional[str]:
        """
        Builds the prompt for the current rotation mode and calls the LLM router.

        Returns the message string on success, or None if:
          - The LLM chose silence (STAY_SILENT token)
          - The response was too short to be meaningful
          - An exception occurred

        IMPORTANT: Does NOT call mark_triggered() internally.
        The caller (scheduler.proactive_check) must call mark_triggered() AFTER
        the message has been successfully delivered to Telegram. This ensures
        a failed delivery does not consume the cooldown window.
        """
        try:
            prompt  = self.build_prompt(chat_service, session_id, memory_service)
            message = llm_router.get_response(prompt).strip()

            # Respect the LLM's explicit silence signal
            if not message or _SILENT_SIGNAL in message:
                logger.info("[PROACTIVE] LLM chose silence for mode %d.", self.trigger_count % 3)
                return None

            if len(message) < 5:
                logger.debug("[PROACTIVE] Response too short to send (%d chars).", len(message))
                return None

            logger.info(
                "[PROACTIVE] Message ready (mode %d, trigger #%d): %.80s...",
                self.trigger_count % 3,
                self.trigger_count + 1,   # +1 because mark_triggered hasn't run yet
                message,
            )
            return message

        except Exception as e:
            logger.error("[PROACTIVE] Failed to generate proactive message: %s", e)
            return None
