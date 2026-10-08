import asyncio
import json
import os
import sys
import time
from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Ana dizini Python path'ine ekle
sys.path.append(BASE_DIR)

try:
    from main import AgenticDemoChatbot
    from config import Config
except ImportError:
    AgenticDemoChatbot = None
    Config = None

# Kötüye kullanıma karşı basit sınırlar (herkese açık bir WebSocket, Gemini kotasını harcar)
MAX_MESSAGE_CHARS = int(os.getenv("MAX_MESSAGE_CHARS", 2000))
RATE_LIMIT_MESSAGES = int(os.getenv("RATE_LIMIT_MESSAGES", 20))   # bağlantı başına
RATE_LIMIT_WINDOW_S = int(os.getenv("RATE_LIMIT_WINDOW_S", 60))
THINKING_DELAY_S = float(os.getenv("THINKING_DELAY_S", 1.0))      # "düşünüyor" göstergesi için

# Global chatbot instance
chatbot = None


def _init_chatbot():
    """Bloklayan başlatma işi (embedding çağrıları dahil); event loop dışında çalıştırılır."""
    bot = AgenticDemoChatbot()
    try:
        bot.setup_database()
    except Exception as db_error:
        print(f"⚠️ Database kurulum hatası (devam ediliyor): {db_error}")
    return bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    global chatbot
    try:
        if AgenticDemoChatbot:
            chatbot = await asyncio.to_thread(_init_chatbot)
            print("✅ Chatbot başlatıldı")
        else:
            print("❌ Chatbot sınıfları yüklenemedi")
    except Exception as e:
        print(f"❌ Chatbot başlatma hatası: {e}")
    yield


app = FastAPI(lifespan=lifespan)


class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)


manager = ConnectionManager()


async def send(websocket: WebSocket, type_: str, content: str = "", **extra):
    await manager.send_message(json.dumps({"type": type_, "content": content, **extra}), websocket)


@app.get("/")
async def read_index():
    return FileResponse(os.path.join(BASE_DIR, "public", "index.html"))


@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {
        "status": "healthy" if chatbot is not None else "starting",
        "message": "Flu Akademi Chatbot API",
        "chatbot_ready": chatbot is not None,
        "offline_demo": bool(Config and Config.OFFLINE),
    }


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await manager.connect(websocket)
    recent = deque()  # son mesajların zaman damgaları (rate limit)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                user_message = str(json.loads(data).get("message", ""))
            except (json.JSONDecodeError, AttributeError):
                await send(websocket, "error", "❌ Geçersiz mesaj biçimi.")
                continue

            if not user_message.strip():
                continue

            if len(user_message) > MAX_MESSAGE_CHARS:
                await send(websocket, "error", f"❌ Mesaj çok uzun (en fazla {MAX_MESSAGE_CHARS} karakter).")
                continue

            now = time.monotonic()
            while recent and now - recent[0] > RATE_LIMIT_WINDOW_S:
                recent.popleft()
            if len(recent) >= RATE_LIMIT_MESSAGES:
                await send(websocket, "error", "⏳ Çok hızlı mesaj gönderiyorsunuz, lütfen biraz bekleyin.")
                continue
            recent.append(now)

            # Bot yanıtını başlat
            await send(websocket, "bot_thinking", "🤔 Model analiz ediyor...")

            if chatbot is None:
                await send(websocket, "error", "❌ Chatbot henüz hazır değil. Lütfen bekleyin.")
                continue

            # Thinking indicator'ın görünmesi için minimum gecikme
            await asyncio.sleep(THINKING_DELAY_S)

            # Streaming yanıt başlat (sadece frontend'e stream başlıyor sinyali)
            await send(websocket, "bot_start")

            try:
                full_response = ""
                stream = chatbot.ask_question_agentic_stream(user_message)
                done = object()
                while True:
                    # Gemini çağrıları senkron/bloklayıcı: event loop'u kilitlememek için thread'de çalıştır
                    chunk = await asyncio.to_thread(next, stream, done)
                    if chunk is done:
                        break
                    if chunk:
                        full_response += chunk
                        await send(websocket, "bot_chunk", chunk, full_content=full_response)

                # Yanıt tamamlandı
                await send(websocket, "bot_complete", full_response)

            except Exception as e:
                print(f"❌ Yanıt hatası: {e}")  # ayrıntı yalnızca sunucu logunda
                await send(websocket, "error", "❌ Yanıt oluşturulurken bir hata oluştu.")

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Static files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "public")), name="static")

# For local development
if __name__ == "__main__":
    import uvicorn
    # Render için port ayarı
    port = int(os.getenv("PORT", 8000))
    host = "0.0.0.0"

    print(f"🌟 Server başlatılıyor... Host: {host}, Port: {port}")
    uvicorn.run(app, host=host, port=port)
