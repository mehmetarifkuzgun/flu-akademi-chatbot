"""Run the real app in offline demo mode and capture README screenshots.

    pip install -r requirements.txt playwright && playwright install chromium
    python scripts/capture_screenshots.py          # writes docs/img/*.png

Answers shown are scripted (see offline.py) and say so on screen. Uses sample_data/, not real course data.
"""
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "img"
PORT = 8123
QUESTIONS = ["Yerleşik hayata geçişin sonuçları nelerdir?"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "CHATBOT_OFFLINE": "1", "PORT": str(PORT), "THINKING_DELAY_S": "0.6",
           "TRANSCRIPT_FILE": str(ROOT / "sample_data" / "transcript.txt"),
           "BOOK_FILE": str(ROOT / "sample_data" / "book.txt"),
           "VECTOR_DB_PATH": tempfile.mkdtemp(prefix="flu-shot-")}
    srv = subprocess.Popen([sys.executable, "api/index.py"], cwd=ROOT, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                if b'"chatbot_ready":true' in urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1).read():
                    break
            except Exception:
                pass
            time.sleep(1)
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{PORT}")
            page.wait_for_selector("#offline-banner")
            time.sleep(1)
            page.screenshot(path=str(OUT / "chat-empty.png"))
            for q in QUESTIONS:
                page.fill("#chat-input", q)
                page.press("#chat-input", "Enter")
                time.sleep(3.5)
            page.screenshot(path=str(OUT / "chat-answer.png"))
            b.close()
    finally:
        srv.terminate()


if __name__ == "__main__":
    main()
