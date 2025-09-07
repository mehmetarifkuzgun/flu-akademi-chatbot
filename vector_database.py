"""
Vektör veritabanı modülü
Bu modül Chroma vektör veritabanı işlemlerini yönetir.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from config import Config

class VectorDatabase:
    """Chroma vektör veritabanı sınıfı"""
    
    def __init__(self):
        """Chroma istemcisini başlat"""
        self.client = chromadb.PersistentClient(
            path=Config.VECTOR_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        print(f"✅ Vektör veritabanı başlatıldı: {Config.VECTOR_DB_PATH}")
    
    def create_collection(self, collection_name: str) -> chromadb.Collection:
        """
        Koleksiyon oluştur veya mevcut olanı al
        
        Args:
            collection_name: Koleksiyon adı
            
        Returns:
            Chroma koleksiyonu
        """
        try:
            # Önce koleksiyonu silmeye çalış (yeniden oluşturmak için)
            try:
                self.client.delete_collection(collection_name)
                print(f"🗑️  Eski koleksiyon silindi: {collection_name}")
            except:
                pass
            
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"✅ Koleksiyon oluşturuldu: {collection_name}")
            return collection
            
        except Exception as e:
            print(f"❌ Koleksiyon oluşturma hatası: {e}")
            raise
    
    def add_documents(self, collection: chromadb.Collection, texts: List[str], 
                     embeddings: List[List[float]], metadatas: List[Dict[str, Any]] = None):
        """
        Koleksiyona dökümanlar ekle
        
        Args:
            collection: Hedef koleksiyon
            texts: Metinler
            embeddings: Embedding vektörleri
            metadatas: Metadata bilgileri
        """
        try:
            if not metadatas:
                metadatas = [{"index": i} for i in range(len(texts))]
            
            ids = [f"doc_{i}" for i in range(len(texts))]
            
            collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            print(f"✅ {len(texts)} döküman koleksiyona eklendi")
            
        except Exception as e:
            print(f"❌ Döküman ekleme hatası: {e}")
            raise
    
    def search_similar(self, collection: chromadb.Collection, query_embedding: List[float], 
                      n_results: int = 3) -> Dict[str, Any]:
        """
        Benzer dökümanları ara
        
        Args:
            collection: Arama yapılacak koleksiyon
            query_embedding: Sorgu embedding'i
            n_results: Döndürülecek sonuç sayısı
            
        Returns:
            Arama sonuçları
        """
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            return results
            
        except Exception as e:
            print(f"❌ Arama hatası: {e}")
            return {"documents": [[]], "distances": [[]], "metadatas": [[]]}
    
    def get_collection(self, collection_name: str) -> Optional[chromadb.Collection]:
        """
        Mevcut koleksiyonu al
        
        Args:
            collection_name: Koleksiyon adı
            
        Returns:
            Chroma koleksiyonu veya None
        """
        try:
            return self.client.get_collection(collection_name)
        except:
            return None
    
    def list_collections(self) -> List[str]:
        """
        Mevcut koleksiyonları listele
        
        Returns:
            Koleksiyon adlarının listesi
        """
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
        except:
            return []
