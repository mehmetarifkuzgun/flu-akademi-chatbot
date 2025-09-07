"""
Metin işleme modülü
Bu modül dosya okuma ve metni parçalama işlemlerini gerçekleştirir.
"""

import os
from typing import List, Tuple

class TextProcessor:
    """Metin işleme sınıfı"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Args:
            chunk_size: Her parçanın maksimum karakter sayısı
            chunk_overlap: Parçalar arası örtüşme miktarı
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def read_file(self, file_path: str) -> str:
        """
        Dosyayı okur
        
        Args:
            file_path: Okunacak dosyanın yolu
            
        Returns:
            Dosya içeriği
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            print(f"✅ Dosya başarıyla okundu: {file_path}")
            return content
            
        except Exception as e:
            print(f"❌ Dosya okuma hatası: {e}")
            return ""
    
    def create_chunks(self, text: str) -> List[str]:
        """
        Metni küçük parçalara böler
        
        Args:
            text: Bölünecek metin
            
        Returns:
            Metin parçalarının listesi
        """
        if not text.strip():
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Parça sonunu belirle
            end = start + self.chunk_size
            
            # Eğer metin bitmediyse, kelime sınırında kes
            if end < len(text):
                # Geriye doğru git ve boşluk bul
                while end > start and text[end] not in [' ', '\n', '\t', '.', '!', '?']:
                    end -= 1
                
                # Eğer boşluk bulunamazsa, zorunlu kes
                if end == start:
                    end = start + self.chunk_size
            
            # Parçayı al
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Bir sonraki başlangıç noktasını belirle (örtüşme ile)
            start = end - self.chunk_overlap
            if start < 0:
                start = end
        
        print(f"✅ Metin {len(chunks)} parçaya bölündü")
        return chunks
    
    def process_files(self, file_paths: List[str]) -> List[Tuple[str, List[str]]]:
        """
        Birden fazla dosyayı işler
        
        Args:
            file_paths: İşlenecek dosya yolları
            
        Returns:
            (dosya_adı, chunks) tuple'larının listesi
        """
        processed_files = []
        
        for file_path in file_paths:
            print(f"\n📖 İşleniyor: {file_path}")
            
            content = self.read_file(file_path)
            if content:
                chunks = self.create_chunks(content)
                file_name = os.path.basename(file_path)
                processed_files.append((file_name, chunks))
            else:
                print(f"⚠️  Dosya boş veya okunamadı: {file_path}")
        
        return processed_files
