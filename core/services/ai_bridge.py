# core/services/ai_bridge.py

import time
import logging
import requests
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class AIBridgeService:
    def __init__(self):
        self.api_key = os.getenv("AI_API_KEY")

    # ======================================
    # GENERIC SAFE CALL (RETRY LOGIC)
    # ======================================
    def safe_call(self, func, *args, **kwargs):
        retries = 3

        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Attempt {attempt+1} failed: {str(e)}")
                time.sleep(2)

        return None

    # ======================================
    # 1. LLM - GENERATE QUESTION
    # ======================================
    def generate_question(self, prompt):
        def api_call():
            # 🔴 Replace with real API later
            return f"AI Question: {prompt}"

        return self.safe_call(api_call) or "Default Question"

    # ======================================
    # 2. TEXT TO SPEECH
    # ======================================
    def text_to_speech(self, text, voice="female", language="en"):
        def api_call():
            # 🔴 Simulated audio response
            return f"AUDIO({text})"

        return self.safe_call(api_call)

    # ======================================
    # 3. SPEECH TO TEXT
    # ======================================
    def speech_to_text(self, audio_file):
        def api_call():
            # 🔴 Simulated conversion
            return "This is a simulated candidate response"

        return self.safe_call(api_call)