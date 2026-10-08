"""
Embedding modülü
Bu modül Google AI embeddings kullanarak metinleri vektörlere çevirir.
"""

import google.generativeai as genai
from typing import List
from config import Config

class EmbeddingGenerator:
    """Google embedding oluşturucu sınıfı"""
    
    def __init__(self):
        """Google AI istemcisini başlat"""
        self.offline = Config.OFFLINE
        self.model = Config.EMBEDDING_MODEL
        if self.offline:
            print("🧪 Çevrimdışı mod: hash tabanlı embedding kullanılıyor (Google API çağrılmaz)")
            return
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        print("✅ Google Embeddings başlatıldı")
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Metinler için embeddings oluştur
        
        Args:
            texts: Embedding oluşturulacak metinler
            
        Returns:
            Embedding vektörlerinin listesi
        """
        if self.offline:
            from offline import hash_embedding
            return [hash_embedding(t) for t in texts]
        try:
            print(f"🔄 {len(texts)} metin için Google embeddings oluşturuluyor...")
            
            embeddings = []
            # Rate limiting için her 10 istekte bir kısa bekleme
            for i, text in enumerate(texts):
                if i > 0 and i % 10 == 0:
                    print(f"   🔄 {i}/{len(texts)} tamamlandı...")
                    import time
                    time.sleep(1)  # 1 saniye bekle
                
                result = genai.embed_content(
                    model=self.model,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
            
            print(f"✅ {len(embeddings)} Google embedding başarıyla oluşturuldu")
            return embeddings
            
        except Exception as e:
            print(f"❌ Google embedding oluşturma hatası: {e}")
            return []
    
    def generate_single_embedding(self, text: str) -> List[float]:
        """
        Tek bir metin için embedding oluştur
        
        Args:
            text: Embedding oluşturulacak metin
            
        Returns:
            Embedding vektörü
        """
        if self.offline:
            from offline import hash_embedding
            return hash_embedding(text)
        try:
            print("🔄 Sorgu için Google embedding oluşturuluyor...")
            result = genai.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_query"
            )
            print("✅ Sorgu embedding'i oluşturuldu")
            return result['embedding']
        except Exception as e:
            print(f"❌ Sorgu embedding hatası: {e}")
            return []
