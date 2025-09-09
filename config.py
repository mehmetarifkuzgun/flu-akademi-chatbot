"""
Konfigürasyon modülü
Bu modül uygulama genelindeki ayarları yönetir.
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Uygulama konfigürasyon sınıfı"""
    
    # API Keys
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # Embedding Settings - Google'ın embedding modeli
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/embedding-001")
    
    # Chunk Settings
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))
    
    # Vector DB Settings - Render uyumlu path
    VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "/var/data/chroma_db" if os.getenv("RENDER") else "./chroma_db")
    
    # Collection Names
    TRANSCRIPT_COLLECTION = "transcript_collection"
    BOOK_COLLECTION = "book_collection"
    
    # File Paths
    TRANSCRIPT_FILE = "transcript.txt"
    BOOK_FILE = "kitap.txt"
    
    @classmethod
    def validate_config(cls):
        """Konfigürasyonu doğrula"""
        missing_keys = []
        
        if not cls.GOOGLE_API_KEY:
            missing_keys.append("GOOGLE_API_KEY")
            
        if missing_keys:
            print("⚠️  Eksik API anahtarları:")
            for key in missing_keys:
                print(f"   - {key}")
            print("Lütfen .env dosyasını kontrol edin.")
            return False
        
        return True
