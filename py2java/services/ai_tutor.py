"""Configuración y límites del Tutor IA (Gemini)."""

import os


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


AI_TUTOR_MAX_CODE_CHARS = 4000


AI_TUTOR_MAX_QUESTION_CHARS = 1000


AI_TUTOR_MAX_EXERCISE_Q_CHARS = 1000


AI_TUTOR_MAX_HISTORY_ITEMS = 12


AI_TUTOR_MAX_HISTORY_ENTRY_CHARS = 1000


AI_TUTOR_MAX_HISTORY_TOTAL_CHARS = 4000
