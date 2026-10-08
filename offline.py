"""Çevrimdışı (offline) demo modu / Offline demo mode.

``CHATBOT_OFFLINE=1`` ile Gemini yerine bu iki yerel bileşen kullanılır:

* ``hash_embedding`` - gerçek ama kaba bir bag-of-words embedding (özellik hashing).
  Chroma üzerindeki vektör araması bununla da gerçektir.
* ``ScriptedModel`` - bir dil modeli DEĞİLDİR. Kodun ürettiği prompt'a bakıp
  (karar prompt'u mu, final prompt'u mu) bağlamdaki cümlelerden deterministik bir
  yanıt derler. Amaç: prompt zinciri, araç seçimi, Chroma araması, WebSocket akışı ve
  arayüzü API anahtarı olmadan çalıştırıp test edebilmek.

These are stand-ins for demos and tests: output is scripted, not model output.
"""
import re
import zlib
from types import SimpleNamespace
from typing import Iterator, List

import numpy as np

DIM = 256
_WORD = re.compile(r"[\wçğıöşüÇĞİÖŞÜ]+", re.UNICODE)
_STOP = {"nedir", "neden", "nasıl", "hakkında", "bana", "için", "ile", "olan", "bir", "bu", "şu"}


def _stem(token: str) -> str:
    # Türkçe ekleri kabaca yok saymak için ilk 5 harf
    return token.lower()[:5]


def _tokens(text: str) -> List[str]:
    return [_stem(t) for t in _WORD.findall(text.lower()) if len(t) > 2 and t not in _STOP]


def hash_embedding(text: str) -> List[float]:
    vec = np.zeros(DIM, dtype=np.float32)
    for tok in _tokens(text):
        h = zlib.crc32(tok.encode("utf-8"))
        vec[h % DIM] += 1.0 if (h >> 16) & 1 else -1.0
        vec[(h >> 8) % DIM] += 0.5
    norm = np.linalg.norm(vec)
    return (vec / norm if norm else vec).tolist()


MARKER = "🧪 *Çevrimdışı demo: bu yanıt bir dil modeli tarafından üretilmedi, getirilen metinlerden derlendi.*"


class ScriptedModel:
    """``genai.GenerativeModel.generate_content`` benzeri arayüz (text / stream)."""

    def generate_content(self, prompt: str, stream: bool = False):
        text = self._reply(prompt)
        if stream:
            return self._stream(text)
        return SimpleNamespace(text=text)

    @staticmethod
    def _stream(text: str) -> Iterator:
        words = text.split(" ")
        for i in range(0, len(words), 6):
            yield SimpleNamespace(text=" ".join(words[i:i + 6]) + (" " if i + 6 < len(words) else ""))

    # ------------------------------------------------------------------
    @staticmethod
    def _question(prompt: str) -> str:
        m = re.search(r"KULLANICI SORUSU:\s*(.+)", prompt)
        return m.group(1).strip() if m else ""

    def _reply(self, prompt: str) -> str:
        question = self._question(prompt)
        if "KARAR VER" in prompt:  # araç seçimi (decision) adımı
            q = question.lower()
            if re.fullmatch(r"(merhaba|selam|teşekkürler|sağ ol)[!. ]*", q):
                return "NO_SEARCH"
            if re.search(r"kitap|teori|kuram|bott", q):
                return "BOOK_ONLY"
            if re.search(r"\bders|derste|hoca", q):
                return "TRANSCRIPT_ONLY"
            return "BOTH_SOURCES"
        # final yanıt adımı
        if "BAĞLAM BİLGİLERİ" not in prompt:
            return f"{MARKER}\n\nBu soru için elimde ders kaynağı yok; çevrimdışı demo modunda genel bilgi üretemiyorum."
        source = re.search(r"Kaynak:\s*(.+)", prompt)
        context = prompt.split("BAĞLAM BİLGİLERİ:", 1)[1].split("KULLANICI SORUSU:", 1)[0]
        context = re.sub(r"^\s*Kaynak:.*$", "", context, flags=re.M)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", context)) if len(s.strip()) > 30]
        q_tokens = set(_tokens(question))
        score = lambda i: len(q_tokens & set(_tokens(sentences[i])))
        best = [i for i in sorted(range(len(sentences)), key=lambda i: -score(i))[:1] if score(i)] or [0]
        # en iyi cümle + hemen ardından gelen iki cümle (bağlam için), özgün sırayla
        picked = sorted({j for i in best for j in (i, i + 1, i + 2) if j < len(sentences)})
        top = [sentences[j] for j in picked]
        bullets = "\n".join(f"- {s}" for s in top)
        return (f"{MARKER}\n\nGetirilen kaynaklardaki en ilgili bilgiler:\n\n{bullets}\n\n"
                f"**Kaynak:** {source.group(1).strip() if source else 'bağlam'}")
