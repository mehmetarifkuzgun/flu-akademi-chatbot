"""
Google Gemini AI modülü - Agentic Approach
Bu modül Google Gemini'yi agent olarak kullanır, kendi kararlarını verir.
"""

import google.generativeai as genai
from typing import List, Dict, Any, Callable
from config import Config

class AgenticGeminiChatbot:
    """Agentic Google Gemini chatbot sınıfı"""
    
    def __init__(self):
        """Gemini API'yi yapılandır"""
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-flash') #flash
        
        # Araçları sakla
        self.available_tools = {}
        print("✅ Agentic Google Gemini modeli başlatıldı")
    
    def register_tool(self, name: str, func: Callable, description: str):
        """
        Gemini'nin kullanabileceği araçları kaydet
        
        Args:
            name: Araç adı
            func: Çağrılacak fonksiyon
            description: Aracın açıklaması
        """
        self.available_tools[name] = {
            'function': func,
            'description': description
        }
        print(f"🔧 Araç kaydedildi: {name}")
    
    def decide_and_respond(self, query: str) -> str:
        """
        Kullanıcı sorusuna göre hangi araçları kullanacağına karar verir ve yanıt oluşturur
        
        Args:
            query: Kullanıcı sorusu
            
        Returns:
            Final yanıt
        """
        try:
            # İlk karar verme promptu
            decision_prompt = self._create_decision_prompt(query)
            
            # Model karar veriyor - debug print kaldırıldı
            decision_response = self.model.generate_content(decision_prompt)
            
            if not decision_response.text:
                return "Üzgünüm, karar veremiyorum."
            
            decision = decision_response.text.strip()
            # Model kararı debug print kaldırıldı
            
            # Karara göre araçları kullan ve bilgi topla
            context_data = self._execute_decision(decision, query)
            
            # Final yanıt oluştur
            final_response = self._generate_final_response(query, context_data, decision)
            
            return final_response
            
        except Exception as e:
            print(f"❌ Agentic yanıt hatası: {e}")
            return f"Hata oluştu: {str(e)}"
    
    def decide_and_respond_stream(self, query: str):
        """
        Streaming versiyonu
        """
        try:
            # İlk karar verme
            decision_prompt = self._create_decision_prompt(query)
            
            # Model karar veriyor - debug print kaldırıldı
            decision_response = self.model.generate_content(decision_prompt)
            
            if not decision_response.text:
                yield "Üzgünüm, karar veremiyorum."
                return
            
            decision = decision_response.text.strip()
            # Model kararı debug print kaldırıldı
            
            # Karara göre araçları kullan
            context_data = self._execute_decision(decision, query)
            
            # Streaming final yanıt
            final_prompt = self._create_final_prompt(query, context_data, decision)
            
            response = self.model.generate_content(final_prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            print(f"❌ Agentic streaming hatası: {e}")
            yield f"Hata oluştu: {str(e)}"
    
    def _create_decision_prompt(self, query: str) -> str:
        """Karar verme promptu oluştur"""
        tools_description = "\n".join([
            f"- {name}: {info['description']}" 
            for name, info in self.available_tools.items()
        ])
        
        prompt = f"""Sen bir akıllı asistansın. Kullanıcının sorusuna en iyi şekilde yanıt verebilmek için hangi kaynakları kullanman gerektiğine karar ver.

MEVCUT ARAÇLAR:
{tools_description}

KULLANICI SORUSU: {query}

KARAR VER: Yukarıdaki soruya yanıt verebilmek için hangi araçları kullanman gerekiyor? 

Sadece şu formatlardan birini kullan:
- "TRANSCRIPT_ONLY" - Sadece ders notları/transcript gerekli
- "BOOK_ONLY" - Sadece kitap bilgisi gerekli  
- "BOTH_SOURCES" - Her iki kaynak da gerekli
- "NO_SEARCH" - Genel bilgi, arama gerekmez

Kararını tek kelime olarak ver, açıklama yapma."""

        return prompt
    
    def _execute_decision(self, decision: str, query: str) -> Dict[str, Any]:
        """Karara göre araçları çalıştır"""
        context_data = {
            'transcript_docs': [],
            'book_docs': [],
            'source_info': '',
            'query': query
        }
        
        decision = decision.upper().strip()
        
        if 'TRANSCRIPT_ONLY' in decision:
            if 'search_transcript' in self.available_tools:
                result = self.available_tools['search_transcript']['function'](query)
                context_data['transcript_docs'] = result.get('documents', [])
                context_data['source_info'] = 'Ders İçeriği (model kararı)'
                # Debug print kaldırıldı
        
        elif 'BOOK_ONLY' in decision:
            if 'search_book' in self.available_tools:
                result = self.available_tools['search_book']['function'](query)
                context_data['book_docs'] = result.get('documents', [])
                context_data['source_info'] = 'Kitap (model kararı)'
                # Debug print kaldırıldı
        
        elif 'BOTH_SOURCES' in decision:
            if 'search_transcript' in self.available_tools:
                result = self.available_tools['search_transcript']['function'](query)
                context_data['transcript_docs'] = result.get('documents', [])
            
            if 'search_book' in self.available_tools:
                result = self.available_tools['search_book']['function'](query)
                context_data['book_docs'] = result.get('documents', [])
            
            context_data['source_info'] = 'Ders İçeriği + Kitap (model kararı)'
            # Debug print kaldırıldı
        
        else:  # NO_SEARCH
            context_data['source_info'] = 'Genel bilgi (arama yok)'
            # Debug print kaldırıldı
        
        return context_data
    
    def _generate_final_response(self, query: str, context_data: Dict[str, Any], decision: str) -> str:
        """Final yanıt oluştur"""
        final_prompt = self._create_final_prompt(query, context_data, decision)
        response = self.model.generate_content(final_prompt)
        return response.text if response.text else "Yanıt oluşturulamadı."
    
    def _create_final_prompt(self, query: str, context_data: Dict[str, Any], decision: str) -> str:
        """Final yanıt promptu"""
        
        all_docs = context_data['transcript_docs'] + context_data['book_docs']
        context_text = "\n\n".join(all_docs) if all_docs else ""
        
        if context_text:
            prompt = f"""Sen yardımsever bir ders asistanısın. Kullanıcının sorusunu verilen bağlam bilgileri kullanarak yanıtla.

BAĞLAM BİLGİLERİ:
Kaynak: {context_data['source_info']}

{context_text}

KULLANICI SORUSU: {query}

Bu bilgileri kullanarak detaylı ve yararlı bir yanıt ver. Ders içeriğinden bahsederken "hocanın dersinde..." şeklinde ifade et. Hangi kaynaktan bilgi aldığını belirt."""
        
        else:
            prompt = f"""Sen yardımsever bir asistansın. Genel bilginle kullanıcının sorusunu yanıtla.

KULLANICI SORUSU: {query}

Genel bilginle yardımcı bir yanıt ver."""
        
        return prompt
    
    def generate_response(self, query: str, context_documents: List[str], 
                         source_info: str = "") -> str:
        """
        Verilen sorgu ve bağlam kullanarak yanıt oluştur
        
        Args:
            query: Kullanıcı sorusu
            context_documents: Bağlam dökümanları
            source_info: Kaynak bilgisi (transcript/kitap)
            
        Returns:
            Oluşturulan yanıt
        """
        try:
            # Bağlam metni oluştur
            context = "\n\n".join(context_documents) if context_documents else ""
            
            # Prompt oluştur
            prompt = self._create_prompt(query, context, source_info)
            
            # Yanıt oluştur
            response = self.model.generate_content(prompt)
            
            return response.text if response.text else "Üzgünüm, yanıt oluşturamadım."
            
        except Exception as e:
            print(f"❌ Yanıt oluşturma hatası: {e}")
            return f"Hata oluştu: {str(e)}"
    
    def generate_response_stream(self, query: str, context_documents: List[str], 
                               source_info: str = ""):
        """
        Verilen sorgu ve bağlam kullanarak streaming yanıt oluştur
        
        Args:
            query: Kullanıcı sorusu
            context_documents: Bağlam dökümanları
            source_info: Kaynak bilgisi (transcript/kitap)
            
        Yields:
            Yanıt parçaları
        """
        try:
            # Bağlam metni oluştur
            context = "\n\n".join(context_documents) if context_documents else ""
            
            # Prompt oluştur
            prompt = self._create_prompt(query, context, source_info)
            
            # Streaming yanıt oluştur
            response = self.model.generate_content(prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            print(f"❌ Streaming yanıt hatası: {e}")
            yield f"Hata oluştu: {str(e)}"
    
    def _create_prompt(self, query: str, context: str, source_info: str) -> str:
        """
        Chatbot için prompt oluştur
        
        Args:
            query: Kullanıcı sorusu
            context: Bağlam metni
            source_info: Kaynak bilgisi
            
        Returns:
            Oluşturulan prompt
        """
        base_prompt = """Sen yardımsever bir ders asistanısın. Kullanıcının sorularını mevcut bağlam bilgileri kullanarak yanıtlıyorsun.

ÖNEMLI KURALLAR:
1. Ders içeriği bilgisi daha önceliklidir.
2. Gerektiğinde kitap bilgisini kullanabilirsin.
3. Bağlam bilgilerinde yanıt yoksa, kibarca bilmediğini belirt.
4. Yanıtlarını Türkçe ver.
5. Hangi kaynaktan bilgi aldığını belirt.
6. İnsanlara konuyu anlamalarında yardımcı ol. Bu esnada yorum yapman, örnek vermen gerekiyorsa ver.
7. Doğrudan ders metnini yazmak yerine bunu öğrencinin anlaması için daha detaylı anlat. Yorumla ve açıkla.
8. Ders içeriğinden bahsederken "hocanın dersinde..." şeklinde ifade et."""

        if context:
            source_text = f"\n\nKAYNAK: {source_info}" if source_info else ""
            prompt = f"""{base_prompt}

BAĞLAM BİLGİLERİ:{source_text}
{context}

KULLANICI SORUSU: {query}

YANITINIZ:"""
        else:
            prompt = f"""{base_prompt}

Üzgünüm, bu konuda bağlam bilgim bulunmuyor.

KULLANICI SORUSU: {query}

YANITINIZ:"""
        
        return prompt
