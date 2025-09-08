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
    print("✅ AgenticDemoChatbot imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("🔄 Creating minimal vector search chatbot...")
    
    import google.generativeai as genai
    import os
    from typing import List
    
    class MinimalVectorChatbot:
        def __init__(self):
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable is required")
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.embedding_model = genai.GenerativeModel('models/embedding-001')
            
            # In-memory knowledge base
            self.knowledge_base = [
                "Neolitik Devrim, yaklaşık 10.000 yıl önce insanlığın tarım ve hayvancılığa geçişi ile başlayan büyük dönüşümdür.",
                "Bu dönemde insanlar avcı-toplayıcı yaşamdan yerleşik tarım toplumuna geçmiştir.",
                "İlk tarım merkezleri Mezopotamya, Anadolu ve Mısır'da ortaya çıkmıştır.",
                "Tarım devrimi ile birlikte nüfus artışı, şehirleşme ve uzmanlaşma başlamıştır.",
                "Çanak çömlek, dokumacılık ve metal işçiliği bu dönemde gelişmiştir."
            ]
            
        def search_knowledge(self, query: str) -> str:
            # Basit keyword matching ile knowledge search
            query_lower = query.lower()
            relevant_info = []
            
            for info in self.knowledge_base:
                if any(word in info.lower() for word in query_lower.split()):
                    relevant_info.append(info)
            
            return "\n".join(relevant_info[:3]) if relevant_info else ""
            
        def ask_question_stream(self, question: str):
            try:
                # Knowledge base'den ilgili bilgi al
                context = self.search_knowledge(question)
                
                system_prompt = f"""Sen Flu Akademi'nin Neolitik Devrim konusunda uzman bir ders asistanısın. 
                Aşağıdaki bilgileri kullanarak soruyu yanıtla:
                
                {context}
                
                Türkçe yanıt ver ve akademik ama anlaşılır bir dil kullan."""
                
                full_prompt = f"{system_prompt}\n\nSoru: {question}\n\nYanıt:"
                response = self.model.generate_content(full_prompt, stream=True)
                
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
            except Exception as e:
                yield f"❌ Hata: {str(e)}"
                
        def ask_question_agentic_stream(self, question: str):
            # Fallback to normal stream
            return self.ask_question_stream(question)
                    
    AgenticDemoChatbot = MinimalVectorChatbot
    print("✅ MinimalVectorChatbot created successfully")

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
            # Database kurulum denemesi (opsiyonel)
            try:
                if hasattr(chatbot, 'setup_database'):
                    chatbot.setup_database()
                    print("✅ Vector database kurulumu tamamlandı")
                else:
                    print("⚠️ SimpleChatbot kullanılıyor (vector search yok)")
            except Exception as db_error:
                print(f"⚠️ Database kurulum hatası: {db_error}")
                print("🔄 Chatbot vector search olmadan çalışacak")
                # Database hatasında bile chatbot'u başlat
                try:
                    if hasattr(chatbot, '_register_agent_tools_limited'):
                        chatbot._register_agent_tools_limited()
                except:
                    pass
            print("✅ Chatbot başlatıldı")
        else:
            print("❌ Chatbot sınıfları yüklenemedi")
    except Exception as e:
        print(f"❌ Chatbot başlatma hatası: {e}")
        # En kötü durumda bile basit bir chatbot oluştur
        try:
            from gemini_chatbot import AgenticGeminiChatbot
            chatbot = AgenticGeminiChatbot()
            print("✅ Minimal chatbot başlatıldı")
        except Exception as fallback_error:
            print(f"❌ Minimal chatbot bile başlatılamadı: {fallback_error}")

# Static files
app.mount("/static", StaticFiles(directory="public"), name="static")

# For local development
if __name__ == "__main__":
    import uvicorn
    print("🌟 Local development server başlatılıyor...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
