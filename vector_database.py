"""
Vektör veritabanı modülü
Bu modül Chroma vektör veritabanı işlemlerini yönetir.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import os
from config import Config

class VectorDatabase:
    """Chroma vektör veritabanı sınıfı"""
    
    def __init__(self):
        """Chroma istemcisini başlat"""
        try:
            # Render platformu tespiti
            is_render = os.getenv("RENDER") == "true"
            
            # Veritabanı dizininin var olduğundan emin ol
            if not os.path.exists(Config.VECTOR_DB_PATH):
                os.makedirs(Config.VECTOR_DB_PATH, exist_ok=True)
                print(f"📁 Veritabanı dizini oluşturuldu: {Config.VECTOR_DB_PATH}")
            
            # Render'da persistent disk kontrolü
            if is_render:
                # Render persistent disk mount kontrolü
                mount_path = "/var/data"
                if not os.path.exists(mount_path):
                    print(f"⚠️ Persistent disk mount edilmemiş: {mount_path}")
                    print("🔄 Memory-only veritabanına geçiliyor...")
                    self._init_memory_client()
                    return
                
                # Disk yazma izni kontrolü
                test_file = os.path.join(mount_path, "write_test.tmp")
                try:
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    print(f"✅ Persistent disk yazma izni OK: {mount_path}")
                except Exception as write_error:
                    print(f"⚠️ Persistent disk yazma hatası: {write_error}")
                    print("🔄 Memory-only veritabanına geçiliyor...")
                    self._init_memory_client()
                    return

            # Normal persistent client başlatma
            self._init_persistent_client()
            
        except Exception as e:
            print(f"❌ Vektör veritabanı başlatma hatası: {e}")
            print("🔄 Memory-only veritabanına geçiliyor...")
            self._init_memory_client()
            
    def _init_persistent_client(self):
        """Persistent Chroma client başlat"""
        try:
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
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    is_persistent=True
                )
            )
            print(f"✅ Persistent vektör veritabanı başlatıldı: {Config.VECTOR_DB_PATH}")
            
        except Exception as e:
            print(f"❌ Persistent client hatası: {e}")
            raise e
    
    def _init_memory_client(self):
        """Memory-only Chroma client başlat"""
        try:
            print("🔄 Memory-only veritabanına geçiliyor...")
            self.client = chromadb.Client(
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    is_persistent=False
                )
            )
            print("✅ Memory-only vektör veritabanı başlatıldı")
            
        except Exception as e:
            print(f"❌ Memory client hatası: {e}")
            # Son çare: basit in-memory client
            try:
                import chromadb
                self.client = chromadb.Client()
                print("✅ Basit memory client başlatıldı")
            except Exception as final_error:
                print(f"❌ Tüm client seçenekleri başarısız: {final_error}")
                raise final_error
    
    def create_collection(self, collection_name: str,
                          extra_metadata: Optional[Dict[str, Any]] = None) -> chromadb.Collection:
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
                metadata={"hnsw:space": "cosine", **(extra_metadata or {})}
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
