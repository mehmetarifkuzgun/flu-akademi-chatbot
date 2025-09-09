from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
import os
import sys

# Ana dizini Python path'ine ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from main import AgenticDemoChatbot
except ImportError:
    # Vercel'de import sorunu varsa basit bir fallback
    AgenticDemoChatbot = None

app = FastAPI()

# Global chatbot instance
chatbot = None

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

@app.get("/")
async def read_index():
    return FileResponse('public/index.html')

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    global chatbot
    status = "healthy" if chatbot is not None else "starting"
    return {
        "status": status,
        "message": "Flu Akademi Chatbot API",
        "chatbot_ready": chatbot is not None
    }

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            if not user_message.strip():
                continue
            
            # Bot yanıtını başlat
            await manager.send_message(json.dumps({
                "type": "bot_thinking",
                "content": "🤔 Model analiz ediyor..."
            }), websocket)
            
            if chatbot is None:
                await manager.send_message(json.dumps({
                    "type": "error",
                    "content": "❌ Chatbot henüz hazır değil. Lütfen bekleyin."
                }), websocket)
                continue
            
            # Streaming yanıt
            await manager.send_message(json.dumps({
                "type": "bot_start",
                "content": ""
            }), websocket)
            
            try:
                full_response = ""
                for chunk in chatbot.ask_question_agentic_stream(user_message):
                    if chunk:
                        full_response += chunk
                        await manager.send_message(json.dumps({
                            "type": "bot_chunk",
                            "content": chunk,
                            "full_content": full_response
                        }), websocket)
                
                # Yanıt tamamlandı
                await manager.send_message(json.dumps({
                    "type": "bot_complete",
                    "content": full_response
                }), websocket)
                
            except Exception as e:
                await manager.send_message(json.dumps({
                    "type": "error",
                    "content": f"❌ Hata: {str(e)}"
                }), websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    global chatbot
    try:
        if AgenticDemoChatbot:
            chatbot = AgenticDemoChatbot()
            # Chatbot'u kısıtlı modda başlat
            try:
                chatbot.setup_database()
            except Exception as db_error:
                print(f"⚠️ Database kurulum hatası (devam ediliyor): {db_error}")
            print("✅ Chatbot başlatıldı")
        else:
            print("❌ Chatbot sınıfları yüklenemedi")
    except Exception as e:
        print(f"❌ Chatbot başlatma hatası: {e}")

# Static files
app.mount("/static", StaticFiles(directory="public"), name="static")

# For local development
if __name__ == "__main__":
    import uvicorn
    # Render için port ayarı
    port = int(os.getenv("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"🌟 Server başlatılıyor... Host: {host}, Port: {port}")
    uvicorn.run(app, host=host, port=port)
