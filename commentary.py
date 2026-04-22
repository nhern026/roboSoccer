import threading
import subprocess
import time
import os
import anthropic


MODEL = "claude-haiku-4-5-20251001"
COMMENTARY_INTERVAL = 10.0  # seconds between live commentary lines

VOICE = "Malcolm"   # Jamie (Premium) — ID shown as Malcolm in pyttsx3/say
RATE  = 185         # words per minute

SYSTEM_PROMPT = (
    "You are a PASSIONATE, over-the-top robot soccer commentator for a robot car soccer game. "
    "Given the current game state as JSON, generate ONE short, punchy commentary line (max 20 words). "
    "Use ALL CAPS for the most dramatic words. Use exclamation marks. Short, sharp sentences. "
    "Be loud, emotional, and electrifying — like the crowd is going wild. "
    "If ball_x/ball_y are present (0-640 range), use them: low x = left side, high x = right side. "
    "No emojis."
)


class Commentary:
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self._busy = threading.Event()  # set = busy, clear = idle
        self._last_fire = 0.0

    def announce(self, game_state_dict: dict):
        """Fire immediately — used for goal/halftime/game-over events."""
        self._fire(game_state_dict)

    def maybe_announce(self, game_state_dict: dict):
        """Fire only if the cooldown has elapsed — used for live play commentary."""
        if time.time() - self._last_fire < COMMENTARY_INTERVAL:
            return
        self._fire(game_state_dict)

    def _fire(self, game_state_dict: dict):
        if self._busy.is_set():
            return
        self._busy.set()
        self._last_fire = time.time()
        thread = threading.Thread(target=self._run, args=(game_state_dict,), daemon=True)
        thread.start()

    def _run(self, state: dict):
        try:
            line = self._generate(state)
            if line:
                self._speak(line)
        finally:
            self._busy.clear()

    def _generate(self, state: dict) -> str:
        try:
            message = self._client.messages.create(
                model=MODEL,
                max_tokens=60,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": str(state)}],
            )
            return message.content[0].text.strip()
        except Exception as e:
            print(f"[commentary] API error: {e}")
            return ""

    def _speak(self, text: str):
        try:
            print(f"[commentary] {text}")
            subprocess.run(["say", "-v", VOICE, "-r", str(RATE), text])
        except Exception as e:
            print(f"[commentary] TTS error: {e}")
