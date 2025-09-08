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
        try:
            # Veritabanı dizininin var olduğundan emin ol
            import os
            if not os.path.exists(Config.VECTOR_DB_PATH):
                os.makedirs(Config.VECTOR_DB_PATH, exist_ok=True)
            
            # Eski database dosyalarını temizle eğer permission sorunu varsa
            db_file = os.path.join(Config.VECTOR_DB_PATH, "chroma.sqlite3")
            if os.path.exists(db_file):
                try:
                    # Dosya izinlerini kontrol et ve düzelt
                    import stat
                    current_permissions = os.stat(db_file).st_mode
                    os.chmod(db_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)
                except Exception as perm_error:
                    print(f"⚠️ Dosya izinleri düzeltilemedi: {perm_error}")
                    # Sorunlu dosyayı sil ve yeniden oluştur
                    try:
                        os.remove(db_file)
                        print("🔄 Sorunlu veritabanı dosyası silindi, yenisi oluşturulacak")
                    except:
                        print("❌ Sorunlu veritabanı dosyası silinemedi")
            
            self.client = chromadb.PersistentClient(
                path=Config.VECTOR_DB_PATH,
                settings=Settings(anonymized_telemetry=False)
            )
            print(f"✅ Vektör veritabanı başlatıldı: {Config.VECTOR_DB_PATH}")
            
        except Exception as e:
            print(f"❌ Vektör veritabanı başlatma hatası: {e}")
            # Fallback: memory-only client
            try:
                print("🔄 Memory-only veritabanına geçiliyor...")
                self.client = chromadb.Client(
                    settings=Settings(anonymized_telemetry=False)
                )
                print("✅ Memory-only vektör veritabanı başlatıldı")
            except Exception as fallback_error:
                print(f"❌ Memory-only veritabanı da başlatılamadı: {fallback_error}")
                raise
    
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
