"""Tüm testler çevrimdışı modda ve geçici bir Chroma dizininde çalışır (API anahtarı/ağ gerekmez)."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# config.py env değerlerini import anında okuduğu için import'tan ÖNCE ayarla
os.environ["CHATBOT_OFFLINE"] = "1"
os.environ["TRANSCRIPT_FILE"] = str(ROOT / "sample_data" / "transcript.txt")
os.environ["BOOK_FILE"] = str(ROOT / "sample_data" / "book.txt")
os.environ["VECTOR_DB_PATH"] = tempfile.mkdtemp(prefix="flu-chroma-")
os.environ["THINKING_DELAY_S"] = "0"
os.environ.pop("RENDER", None)
