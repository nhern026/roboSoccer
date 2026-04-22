import pyttsx3

VOICES = [
    ("Reed (US)",       "com.apple.eloquence.en-US.Reed"),
    ("Rocko (US)",      "com.apple.eloquence.en-US.Rocko"),
    ("Daniel (UK)",     "com.apple.voice.compact.en-GB.Daniel"),
    ("Allison (US)",    "com.apple.voice.enhanced.en-US.Allison"),
    ("Samantha (US)",   "com.apple.voice.compact.en-US.Samantha"),
    ("Moira (Irish)",   "com.apple.voice.compact.en-IE.Moira"),
    ("Tessa (SA)",      "com.apple.voice.compact.en-ZA.Tessa"),
    ("Karen (AU)",      "com.apple.voice.compact.en-AU.Karen"),
    ("Zarvox (Robot)",  "com.apple.speech.synthesis.voice.Zarvox"),
    ("Fred (Classic)",  "com.apple.speech.synthesis.voice.Fred"),
]

LINE = "Goal! The red team strikes from the left side — what a shot!"

for name, voice_id in VOICES:
    print(f"▶ {name}")
    e = pyttsx3.init()
    e.setProperty("rate", 175)
    e.setProperty("voice", voice_id)
    e.say(f"{name}. {LINE}")
    e.runAndWait()
    del e

print("Done.")
