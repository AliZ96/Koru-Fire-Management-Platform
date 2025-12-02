# KORU Yangın Önleme Platformu

İzmir ilinde yangın riskinin izlenmesi ve yönetilmesi için geliştirilmiş gerçek zamanlı harita tabanlı bir sistem.

## Özellikler

- 🗺️ **İzmir Haritası**: Leaflet.js tabanlı interaktif harita
- 🔥 **Yangın Algılama**: NASA FIRMS uydu verileri ile gerçek zamanlı yangın tespiti
- 💧 **Barajlar**: OpenStreetMap Overpass API ile baraj ve su kaynaklarını gösterme
- 🏢 **Toplanma Alanları**: İzmir ilindeki toplanma alanlarının haritalanması
- 🌪️ **Rüzgâr Analizi**: Gerçek zamanlı rüzgâr verisi ve yangın yayılım tahmini
- ⚠️ **Risk Haritası**: Wind-aligned risk grid ile yangın risk analizi
- 🛡️ **Uydu Haritası**: Esri ArcGIS uydu görüntüleri desteği
- 👤 **Kullanıcı Yönetimi**: Giriş sistemi (Kullanıcı ve Admin rolleri)

## Teknoloji Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Leaflet.js, D3.js, XLSX.js
- **Harita**: OpenStreetMap, Esri ArcGIS
- **Uydu Verisi**: NASA FIRMS API, Overpass API
- **Hava Durumu**: Open-Meteo API

## Kurulum

### Gereksinimler
- Python 3.11+
- pip
- Virtual Environment

### Adımlar

1. **Repository'yi klonlayın**:
   ```bash
   git clone https://github.com/bbgmfun/koru_bitirme.git
   cd koru_bitirme
   ```

2. **Virtual environment oluşturun**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # macOS/Linux
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Bağımlılıkları yükleyin**:
   ```bash
   pip install fastapi uvicorn pydantic requests
   ```

4. **Sunucuyu başlatın**:
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Tarayıcıda açın**:
   ```
   http://localhost:8000
   ```

## Proje Yapısı

```
.
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI uygulaması
│   ├── firms.py          # NASA FIRMS API
│   ├── weather.py        # Hava durumu servisi
│   └── spread.py         # Yangın yayılım modeli
├── static/
│   ├── index.html        # Ana dashboard
│   ├── login.html        # Giriş sayfası
│   ├── data/             # GeoJSON verileri
│   └── img/              # Görseller
├── data/
│   └── firms.json        # Önbelleklenmiş yangın verileri
├── PROJECT.md            # Proje belgeleri
└── README.md             # Bu dosya
```

## Giriş Bilgileri (Demo)

**Kullanıcı:**
- Kullanıcı adı: `user1`
- Şifre: `password123`

**Admin:**
- Kullanıcı adı: `admin`
- Şifre: `admin123`

## Kullanım

1. Giriş sayfasında kullanıcı türünü seçin
2. Haritada etkileşimli olarak veri katmanlarını kontrol edin
3. Yangınları, barajları ve toplanma alanlarını gösterebilirsiniz
4. Rüzgâr ve yangın yayılım tahminlerini kullanın
5. Risk haritasında yüksek risk alanlarını belirleyin

## API Endpoints

- `GET /api/ping` - Sunucu durumu kontrolü
- `GET /api/fires` - NASA FIRMS yangın verileri
- `GET /api/fires_cached` - Önbelleklenmiş yangın verileri
- `GET /api/wind` - Rüzgâr verisi
- `GET /api/spread` - Yangın yayılım tahmini
- `GET /api/risk` - Risk grid'i
- `GET /api/risk_grid` - Risk scalar grid'i
- `GET /api/shelters_manifest` - Toplanma alanları listesi

## Veri Kaynakları

- **NASA FIRMS**: Uydulardan elde edilen yangın algıları
- **OpenStreetMap**: Baraj ve coğrafi veriler
- **Open-Meteo**: Rüzgâr ve hava durumu verileri
- **İzmir Büyükşehir Belediyesi**: Toplanma alanları

## Lisans

Bu proje eğitim amaçlı geliştirilmiştir.

## İletişim

**Telefon**: 153  
**Faks**: (0232) 293 39 95  
**E-Posta**: him@izmir.bel.tr
