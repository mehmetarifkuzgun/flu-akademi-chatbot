"""
Ana chatbot sistemi - Agentic Approach  
Bu modül agentic chatbot'u çalıştırır, model kendi kararlarını verir.
"""

import os
import sys
import time
from typing import List, Tuple, Dict, Any
from config import Config
from text_processor import TextProcessor
from embedding_generator import EmbeddingGenerator
from vector_database import VectorDatabase
from gemini_chatbot import AgenticGeminiChatbot

class AgenticDemoChatbot:
    """Agentic Demo chatbot ana sınıfı"""
    
    def __init__(self):
        """Chatbot bileşenlerini başlat"""
        print("🚀 Agentic Demo Chatbot başlatılıyor...")
        
        # Konfigürasyonu doğrula
        if not Config.validate_config():
            raise Exception("Konfigürasyon doğrulaması başarısız!")
        
        # Bileşenleri başlat
        self.text_processor = TextProcessor(Config.CHUNK_SIZE, Config.CHUNK_OVERLAP)
        self.embedding_generator = EmbeddingGenerator()
        self.vector_db = VectorDatabase()
        self.agent = AgenticGeminiChatbot()  # Agentic chatbot
        
        # Koleksiyonları başlat
        self.transcript_collection = None
        self.book_collection = None
        
        print("✅ Tüm bileşenler başarıyla yüklendi")
    
    def setup_database(self):
        """Veritabanını kurar ve dökümanları yükler"""
        print("\n📊 Veritabanı kurulumu başlıyor...")
        
        # Dosyaları işle
        files_to_process = [
            (Config.TRANSCRIPT_FILE, Config.TRANSCRIPT_COLLECTION),
            (Config.BOOK_FILE, Config.BOOK_COLLECTION)
        ]
        
        for file_path, collection_name in files_to_process:
            if os.path.exists(file_path):
                self._process_and_store_file(file_path, collection_name)
            else:
                print(f"⚠️  Dosya bulunamadı: {file_path}")
        
        # Agentic araçları kaydet
        self._register_agent_tools()
        
        print("✅ Veritabanı kurulumu ve araç kaydı tamamlandı")
    
    def _register_agent_tools(self):
        """Agent'ın kullanabileceği araçları kaydet"""
        
        def search_transcript_tool(query: str) -> Dict[str, Any]:
            """Transcript koleksiyonunda arama yapar"""
            if not self.transcript_collection:
                return {'documents': [], 'source': 'transcript'}
            
            query_embedding = self.embedding_generator.generate_single_embedding(query)
            if not query_embedding:
                return {'documents': [], 'source': 'transcript'}
            
            results = self.vector_db.search_similar(
                self.transcript_collection, query_embedding, n_results=4
            )
            
            docs = results["documents"][0] if results["documents"] and results["documents"][0] else []
            return {'documents': docs, 'source': 'transcript'}
        
        def search_book_tool(query: str) -> Dict[str, Any]:
            """Kitap koleksiyonunda arama yapar"""
            if not self.book_collection:
                return {'documents': [], 'source': 'book'}
            
            query_embedding = self.embedding_generator.generate_single_embedding(query)
            if not query_embedding:
                return {'documents': [], 'source': 'book'}
            
            results = self.vector_db.search_similar(
                self.book_collection, query_embedding, n_results=4
            )
            
            docs = results["documents"][0] if results["documents"] and results["documents"][0] else []
            return {'documents': docs, 'source': 'book'}
        
        # Araçları agent'a kaydet
        self.agent.register_tool(
            'search_transcript', 
            search_transcript_tool,
            'Ders içeriğinde arama yapar. Derste anlatılan konular için kullan.'
        )
        
        self.agent.register_tool(
            'search_book', 
            search_book_tool,
            'Kitap içeriğinde detaylı teorik bilgi arar. Kavramsal açıklamalar için kullan.'
        )
    
    def _register_agent_tools_limited(self):
        """Agent'ın kullanabileceği araçları kaydet - veritabanı olmadan sınırlı mod"""
        
        def limited_search_tool(query: str) -> Dict[str, Any]:
            """Sınırlı arama - veritabanı olmadan basit yanıt"""
            return {
                'documents': [f"Üzgünüm, şu anda veritabanına erişim sorunu yaşıyoruz. '{query}' hakkındaki sorunuzu yanıtlayabilmem için veritabanının çalışır durumda olması gerekiyor."],
                'source': 'limited'
            }
        
        # Sınırlı araçları agent'a kaydet
        self.agent.register_tool(
            'search_transcript', 
            limited_search_tool,
            'Ders içeriğinde arama yapar (sınırlı mod).'
        )
        
        self.agent.register_tool(
            'search_book', 
            limited_search_tool,
            'Kitap içeriğinde arama yapar (sınırlı mod).'
        )
    
    def _process_and_store_file(self, file_path: str, collection_name: str):
        """Dosyayı işler ve veritabanına kaydeder"""
        print(f"\n📄 İşleniyor: {file_path}")
        
        # Dosyayı oku ve parçala
        content = self.text_processor.read_file(file_path)
        if not content:
            return
        
        chunks = self.text_processor.create_chunks(content)
        if not chunks:
            return
        
        # Embeddings oluştur
        embeddings = self.embedding_generator.generate_embeddings(chunks)
        if not embeddings:
            return
        
        # Koleksiyon oluştur ve dökümanları ekle
        collection = self.vector_db.create_collection(collection_name)
        
        metadatas = [{"source": file_path, "chunk_index": i} for i in range(len(chunks))]
        self.vector_db.add_documents(collection, chunks, embeddings, metadatas)
        
        # Koleksiyon referansını sakla
        if collection_name == Config.TRANSCRIPT_COLLECTION:
            self.transcript_collection = collection
        elif collection_name == Config.BOOK_COLLECTION:
            self.book_collection = collection
    
    def ask_question_agentic(self, question: str) -> str:
        """
        Agentic yaklaşımla kullanıcı sorusuna yanıt verir
        Model kendi kararını verir hangi kaynaklara bakacağına
        
        Args:
            question: Kullanıcı sorusu
            
        Returns:
            Chatbot yanıtı
        """
        print(f"\n❓ Soru: {question}")
        
        # Agent'a karar ver ve yanıtla
        response = self.agent.decide_and_respond(question)
        
        return response
    
    def ask_question_agentic_stream(self, question: str):
        """
        Agentic yaklaşımla streaming yanıt verir
        
        Args:
            question: Kullanıcı sorusu
        """
        # Streaming yanıt oluştur - debug print'ler API server için kaldırıldı
        
        full_response = ""
        for chunk in self.agent.decide_and_respond_stream(question):
            full_response += chunk
            yield chunk  # API server için chunk'ları yield et
            time.sleep(0.02)  # Küçük bir gecikme ekleyerek daha doğal görünüm
        
        return full_response
    
    def start_interactive_chat(self):
        """İnteraktif sohbet başlatır"""
        print("\n🤖 Agentic Demo Chatbot hazır! Sorularınızı yazabilirsiniz.")
        print("Çıkmak için 'quit', 'exit' veya 'çık' yazın.")
        print("\n🧠 Agent kendi kararını verir:")
        print("   🎯 Model sorunuzu analiz eder")
        print("   🔧 Gerekli araçları seçer") 
        print("   � Size en iyi yanıtı verir\n")
        
        while True:
            try:
                user_input = input("👤 Siz: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'çık', 'q']:
                    print("👋 Güle güle!")
                    break
                
                if not user_input:
                    continue
                
                # Agentic streaming yanıt kullan
                self.ask_question_agentic_stream(user_input)
                
            except KeyboardInterrupt:
                print("\n👋 Güle güle!")
                break
            except Exception as e:
                print(f"❌ Hata: {e}")

def main():
    """Ana fonksiyon"""
    try:
        # Agentic chatbot'u başlat
        chatbot = AgenticDemoChatbot()
        
        # Veritabanını kur
        chatbot.setup_database()
        
        # İnteraktif sohbeti başlat
        chatbot.start_interactive_chat()
        
    except Exception as e:
        print(f"❌ Chatbot başlatma hatası: {e}")

if __name__ == "__main__":
    main()
