"""Run from the backend folder:  python test_gemini.py
Tries each model directly (no app involved) and prints how long it took, so you can see which model works."""
import os, time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")
from google import genai
from google.genai import types

key = os.getenv("GEMINI_API_KEY", "")
print("Key found:", bool(key) and key != "replace_me", "| length:", len(key))
client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=30000))
for m in ("gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.5-flash"):
    t = time.time()
    try:
        r = client.models.generate_content(model=m, contents="Reply with the single word: ok")
        print(f"{m}: OK in {time.time() - t:.1f}s -> {r.text.strip()[:40]}")
    except Exception as e:
        print(f"{m}: FAILED after {time.time() - t:.1f}s -> {repr(e)[:200]}")
