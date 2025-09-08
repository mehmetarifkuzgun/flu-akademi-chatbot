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
    print("🔄 Creating ultra-minimal smart chatbot...")
    
    import google.generativeai as genai
    import os
    import re
    
    class UltraMinimalChatbot:
        def __init__(self):
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable is required")
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            
            # Neolitik Devrim bilgi tabanı
            self.knowledge_chunks = [
                "Neolitik Devrim: M.Ö. 10.000-8.000 yılları arasında gerçekleşen büyük dönüşüm",
                "Tarım devrimi: İnsanların avcı-toplayıcılıktan tarıma geçişi",
                "Yerleşik hayat: Köyler ve ilk şehirlerin kurulması",
                "Anadolu: Çatalhöyük, Göbekli Tepe gibi önemli Neolitik merkezler",
                "Teknolojik gelişmeler: Çanak çömlek, dokumacılık, tarım aletleri",
                "Toplumsal değişim: Uzmanlaşma, ticaret, sosyal tabakalaşma",
                "Hayvan evcilleştirme: Köpek, koyun, keçi, sığır, domuz",
                "Bitki yetiştirme: Buğday, arpa, mercimek, bezelye",
                "Çevre etkisi: Ormanların azalması, toprak erozyonu",
                "Nüfus artışı: Gıda üretiminin artmasıyla demografik patlama"
            ]
            
        def smart_search(self, query: str) -> str:
            """Basit ama akıllı arama"""
            query_lower = query.lower()
            
            # Anahtar kelime eşleştirme
            relevant_chunks = []
            keywords = query_lower.split()
            
            for chunk in self.knowledge_chunks:
                chunk_lower = chunk.lower()
                score = 0
                for keyword in keywords:
                    if keyword in chunk_lower:
                        score += 1
                    # Benzer kelimeler
                    if keyword in ["tarım", "ziraat"] and any(word in chunk_lower for word in ["tarım", "bitki", "buğday"]):
                        score += 1
                    if keyword in ["şehir", "kent", "yerleşim"] and any(word in chunk_lower for word in ["yerleşik", "köy", "şehir"]):
                        score += 1
                        
                if score > 0:
                    relevant_chunks.append((chunk, score))
            
            # Skora göre sırala ve en iyi 3'ünü al
            relevant_chunks.sort(key=lambda x: x[1], reverse=True)
            return "\n".join([chunk[0] for chunk in relevant_chunks[:3]])
            
        def ask_question_stream(self, question: str):
            try:
                # Akıllı arama ile context bul
                context = self.smart_search(question)
                
                system_prompt = f"""Sen Flu Akademi'nin Neolitik Devrim uzmanı ders asistanısın.

Aşağıdaki kaynak bilgileri kullanarak soruyu yanıtla:
{context}

Kurallar:
- Türkçe yanıt ver
- Akademik ama anlaşılır dil kullan
- Kaynak bilgileri varsa bunları temel al
- Bilgin yoksa genel Neolitik bilgilerini kullan
- Öğrenciye faydalı ve detaylı açıklamalar yap"""
                
                full_prompt = f"{system_prompt}\n\nÖğrenci Sorusu: {question}\n\nYanıt:"
                response = self.model.generate_content(full_prompt, stream=True)
                
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                        
            except Exception as e:
                yield f"❌ Hata: {str(e)}"
                
        def ask_question_agentic_stream(self, question: str):
            """Agentic versiyon - aynı fonksiyonalite"""
            return self.ask_question_stream(question)
                    
    AgenticDemoChatbot = UltraMinimalChatbot
    print("✅ UltraMinimalChatbot created with smart search!")

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
