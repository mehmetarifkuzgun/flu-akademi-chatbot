# Render Deployment Checklist

## ✅ Yapılandırma Dosyaları

- [x] `render.yaml` - Render deployment config
- [x] `Procfile` - Process definition
- [x] `requirements.txt` - Python dependencies
- [x] `runtime.txt` - Python version specification
- [x] `env.example` - Environment variables example

## ✅ Kod Optimizasyonları

- [x] Render platform detection
- [x] Persistent disk configuration for ChromaDB
- [x] Memory fallback for ChromaDB
- [x] Dynamic port configuration
- [x] Health check endpoint
- [x] Error handling for missing files in production
- [x] Environment-aware database setup

## 📋 Deployment Adımları

### 1. Pre-deployment
- [ ] Google AI API Key hazır
- [ ] Repository GitHub'da
- [ ] Tüm dosyalar commit edildi

### 2. Render Dashboard
- [ ] New Web Service oluştur
- [ ] GitHub repository bağla
- [ ] Environment variables ekle:
  - [ ] `GOOGLE_API_KEY`
  - [ ] `PYTHON_VERSION=3.10.18`
  - [ ] `VECTOR_DB_PATH=/var/data/chroma_db`

### 3. Persistent Disk
- [ ] Disk ekle: `/var/data` mount path
- [ ] 1GB boyut seç
- [ ] Disk eklendikten sonra redeploy

### 4. Post-deployment
- [ ] Service "Running" durumda
- [ ] Health check endpoint test: `/health`
- [ ] Web interface çalışıyor: `/`
- [ ] WebSocket bağlantısı OK: `/ws/chat`

## 🔧 Environment Variables

```
GOOGLE_API_KEY=your_actual_api_key
PYTHON_VERSION=3.10.18
VECTOR_DB_PATH=/var/data/chroma_db
```

## 🚀 Render URL

Deploy sonrası URL: `https://flu-akademi-chatbot.onrender.com`

## 🔍 Troubleshooting

### ChromaDB Issues
- Log'larda "Persistent disk yazma izni OK" mesajını kontrol et
- Eğer "Memory-only" mesajı varsa disk problemi var
- Disk mount path `/var/data` olmalı

### API Issues
- `GOOGLE_API_KEY` doğru mu?
- Health check `/health` endpoint'i çalışıyor mu?
- Port 10000 kullanılıyor mu?

### Performance
- Free tier 512MB RAM limit
- Upgrade to Starter ($7/ay) for better performance
- Monitor disk usage
