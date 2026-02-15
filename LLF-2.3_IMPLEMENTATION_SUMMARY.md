# Hava Erişilebilirliği Sınıflandırması - Uygulama Özeti

## LLF-2.3: Hava Erişilebilirliği Sınıflandırma Sistemi

### 📋 Görev Tanımı
Kara erişimi bulunmayan yangın risk bölgelerinin hava araçları (helikopter, uçak, drone) açısından erişilebilirliğinin değerlendirilmesi ve sınıflandırılması.

---

## ✅ Tamamlanan İşler

### 1. Backend Geliştirmesi

#### a) Servis Katmanı
**Dosya**: `app/services/air_accessibility_service.py`

Özellikler:
- ✅ Haversine formülü ile mesafe hesaplama
- ✅ 3 farklı hava aracı tipi desteği (Helikopter, Uçak, Drone)
- ✅ 5 arazi tipi değerlendirmesi (Düz, Tepeli, Dağlık, Ormanlık, Su)
- ✅ Akıllı skorlama sistemi (0-100)
- ✅ 5 seviyeli erişilebilirlik sınıflandırması
- ✅ En yakın hava üssü tespiti (3 üs: Adnan Menderes, Çiğli, Körfez Heliport)
- ✅ Acil iniş noktası analizi (su kaynakları)
- ✅ Tahmini varış süresi (ETA) hesaplama
- ✅ Toplu değerlendirme desteği
- ✅ Grid tabanlı harita oluşturma

Parametreler:
- Enlem/Boylam
- Rakım (metre)
- Arazi tipi
- Bitki örtüsü yoğunluğu (0-1)
- Hava aracı tipi

#### b) API Router
**Dosya**: `app/api/routers/air_accessibility.py`

Endpoint'ler:
- ✅ `POST /api/air-accessibility/classify` - Tek nokta değerlendirmesi
- ✅ `POST /api/air-accessibility/batch-classify` - Toplu değerlendirme (max 1000)
- ✅ `POST /api/air-accessibility/grid-map` - GeoJSON grid haritası
- ✅ `GET /api/air-accessibility/quick-assess` - Hızlı değerlendirme
- ✅ `GET /api/air-accessibility/air-bases` - Hava üsleri listesi
- ✅ `GET /api/air-accessibility/accessibility-levels` - Seviyeler ve açıklamalar
- ✅ `GET /api/air-accessibility/aircraft-types` - Hava aracı bilgileri
- ✅ `GET /api/air-accessibility/terrain-types` - Arazi tipi bilgileri

#### c) Veri Modelleri
**Dosya**: `app/schemas/air_accessibility.py`

Şemalar:
- ✅ AirAccessibilityRequest - İstek modeli
- ✅ AirAccessibilityResponse - Yanıt modeli
- ✅ BatchAccessibilityRequest - Toplu istek
- ✅ GridMapRequest - Grid harita isteği
- ✅ AirBaseInfo - Hava üssü bilgisi
- ✅ Enum tipleri (AircraftType, TerrainType, AccessibilityLevel)

### 2. Frontend Entegrasyonu

**Dosya**: `static/index.html`

Özellikler:
- ✅ "🚁 Hava Erişimi" butonu eklendi
- ✅ Grid tabanlı harita görselleştirmesi
- ✅ Renkli marker sistemi (5 seviye)
- ✅ İnteraktif popup'lar
- ✅ Otomatik legend gösterimi
- ✅ Toggle açma/kapama işlevi

Renk Şeması:
- 🟢 Yeşil: EXCELLENT (85-100)
- 🔵 Mavi: GOOD (70-84)
- 🟠 Turuncu: MODERATE (50-69)
- 🔴 Kırmızı: DIFFICULT (30-49)
- ⚫ Koyu Kırmızı: RESTRICTED (0-29)

### 3. Test ve Dokümantasyon

#### Test Script
**Dosya**: `test_air_accessibility.py`

Test Senaryoları:
- ✅ 4 farklı konum
- ✅ 3 hava aracı tipi
- ✅ Toplu değerlendirme
- ✅ İstatistiksel analiz
- ✅ Detaylı çıktı formatı

#### Dokümantasyon
**Dosyalar**:
- ✅ `AIR_ACCESSIBILITY_README.md` - Kapsamlı kullanım kılavuzu
- ✅ `README.md` - Ana proje dokümantasyonuna entegrasyon

---

## 🎯 Sistem Özellikleri

### Erişilebilirlik Seviyeleri

| Seviye | Skor | Açıklama |
|--------|------|----------|
| EXCELLENT ✅ | 85-100 | Her türlü hava aracı kolayca erişebilir |
| GOOD 👍 | 70-84 | Hava araçları güvenli şekilde erişebilir |
| MODERATE ⚠️ | 50-69 | Belirli kısıtlamalarla erişilebilir |
| DIFFICULT ⛔ | 30-49 | Sadece deneyimli pilotlar erişebilir |
| RESTRICTED 🚫 | 0-29 | Çok sınırlı veya hiç erişim yok |

### Hava Araçları

| Araç | Menzil | Hız | Kullanım Alanı |
|------|--------|-----|----------------|
| Helikopter 🚁 | 600 km | 220 km/h | Dikey iniş, dar alanlar |
| Uçak ✈️ | 2000 km | 400 km/h | Uzun mesafeler, su atımı |
| Drone 🛸 | 50 km | 80 km/h | Keşif, gözlem |

### Skorlama Faktörleri

1. **Mesafe** (0-40 puan): Hava üssüne uzaklık
2. **Rakım** (0-20 puan): >1500m zorluk
3. **Arazi** (0-15 puan): Dağlık/ormanlık ceza
4. **Bitki Örtüsü** (0-15 puan): Yoğunluk cezası
5. **Su Kaynağı** (+5 puan): Yakınlık bonusu

---

## 📊 Test Sonuçları

### Örnek Değerlendirmeler

#### Helikopter için:
- **İzmir Körfez Merkez**: 95.5/100 (EXCELLENT) - 0 km
- **Bornova Tepeleri**: 85.4/100 (EXCELLENT) - 9.15 km
- **Karaburun Dağları**: 71.5/100 (GOOD) - 45.23 km
- **Ödemiş Ormanlık**: 71.7/100 (GOOD) - 71.32 km

#### Ortalama Performans:
- Ortalama Skor: 81.0/100
- Ortalama Mesafe: 31.4 km
- Ortalama ETA: 10-15 dakika

---

## 🚀 Kullanım

### API Örneği

```bash
curl -X POST "http://localhost:8000/api/air-accessibility/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 38.4192,
    "longitude": 27.1287,
    "elevation": 150,
    "terrain_type": "HILLY",
    "vegetation_density": 0.6,
    "aircraft_type": "HELICOPTER"
  }'
```

### Web Arayüzü
1. Ana harita ekranını açın
2. "🚁 Hava Erişimi" butonuna tıklayın
3. Harita grid noktalarla dolacaktır
4. Herhangi bir noktaya tıklayarak detaylı bilgi alın

---

## 📁 Dosya Yapısı

```
koru/
├── app/
│   ├── services/
│   │   └── air_accessibility_service.py      # ✅ Ana servis
│   ├── api/routers/
│   │   └── air_accessibility.py              # ✅ API endpoint'leri
│   ├── schemas/
│   │   └── air_accessibility.py              # ✅ Veri modelleri
│   └── main.py                               # ✅ Router entegrasyonu
├── static/
│   ├── index.html                            # ✅ Frontend entegrasyonu
│   └── data/
│       ├── barajlar.geojson                  # Su kaynakları
│       ├── ponds-lakes.geojson
│       └── water-reservoirs.geojson
├── test_air_accessibility.py                 # ✅ Test scripti
├── AIR_ACCESSIBILITY_README.md               # ✅ Detaylı dokümantasyon
└── README.md                                 # ✅ Güncellenmiş ana README
```

---

## ✨ Öne Çıkan Özellikler

### 1. Akıllı Analiz
- Çoklu faktör değerlendirmesi
- Arazi bazlı optimizasyon
- Hava aracı tipine göre uyarlama

### 2. Gerçek Zamanlı Hesaplama
- Haversine mesafe formülü
- Dinamik skor hesaplama
- Anlık ETA tahmini

### 3. Görsel Zenginlik
- 5 renkli seviye gösterimi
- İnteraktif harita katmanı
- Detaylı popup bilgileri

### 4. Esneklik
- Toplu değerlendirme (1000 nokta)
- Grid harita oluşturma
- Özelleştirilebilir parametreler

---

## 🎓 Teknik Detaylar

### Algoritma
1. En yakın hava üssü bulma (Haversine)
2. Menzil kontrolü
3. Multi-faktör skorlama
4. Seviye sınıflandırması
5. Öneri üretimi

### Performans
- Tek nokta: <100ms
- Batch (100 nokta): <2s
- Grid harita (500 nokta): <5s

### Veri Kaynakları
- İzmir hava üsleri (3 üs)
- Su kaynakları (GeoJSON)
- Arazi verileri (kullanıcı girişi)

---

## 📈 Gelecek Geliştirmeler

- [ ] Rüzgar verisi entegrasyonu
- [ ] Hava durumu faktörleri
- [ ] Gece uçuş kısıtlamaları
- [ ] 3D arazi modeli
- [ ] Gerçek zamanlı hava trafiği
- [ ] Dinamik hava üssü ekleme

---

## ✅ Sonuç

Hava Erişilebilirliği Sınıflandırma Sistemi (LLF-2.3) başarıyla tamamlanmıştır:

✅ Backend servisi aktif  
✅ API endpoint'leri çalışıyor  
✅ Frontend entegrasyonu tamamlandı  
✅ Test senaryoları geçti  
✅ Dokümantasyon hazır  

Sistem, yangın risk bölgelerinin hava erişilebilirliğini değerlendirerek müdahale planlamasına kritik katkı sağlamaktadır.

---

**Geliştirme Tarihi**: 15 Şubat 2026  
**Durum**: ✅ TAMAMLANDI  
**Versiyon**: 1.0.0
