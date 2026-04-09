# Hava Erişilebilirliği Sınıflandırma Sistemi (LLF-2.3)

## Genel Bakış

Kara erişimi bulunmayan yangın risk bölgelerinin hava araçları (helikopter, sabit kanatlı uçak, drone) açısından erişilebilirliğinin değerlendirilmesi için geliştirilmiş akıllı sınıflandırma sistemi.

## Özellikler

### 🎯 Temel Özellikler
- **Çoklu Hava Aracı Desteği**: Helikopter, sabit kanatlı uçak ve drone için optimizasyon
- **Akıllı Skorlama**: 0-100 arası detaylı erişilebilirlik skoru
- **Gerçek Zamanlı Mesafe Hesaplama**: Haversine formülü ile hassas mesafe ölçümü
- **Engel Analizi**: Arazi tipi, rakım, bitki örtüsü değerlendirmesi
- **Acil Durum İniş Noktaları**: En yakın su kaynaklarının tespiti
- **Tahmini Varış Süresi**: Her hava aracı için özelleştirilmiş ETA hesaplama

### 📊 Erişilebilirlik Seviyeleri

| Seviye | Skor Aralığı | Açıklama | İkon |
|--------|--------------|----------|------|
| **EXCELLENT** | 85-100 | Her türlü hava aracı kolayca erişebilir | ✅ |
| **GOOD** | 70-84 | Hava araçları güvenli şekilde erişebilir | 👍 |
| **MODERATE** | 50-69 | Belirli kısıtlamalarla erişilebilir | ⚠️ |
| **DIFFICULT** | 30-49 | Sadece deneyimli pilotlar erişebilir | ⛔ |
| **RESTRICTED** | 0-29 | Çok sınırlı veya hiç erişim yok | 🚫 |

### 🛩️ Desteklenen Hava Araçları

#### Helikopter
- **Menzil**: 600 km
- **Hız**: 220 km/h
- **Avantajlar**: Dikey iniş-kalkış, dar alanlara erişim
- **Kısıtlar**: Hava koşullarına duyarlı

#### Sabit Kanatlı Uçak
- **Menzil**: 2000 km
- **Hız**: 400 km/h
- **Avantajlar**: Uzun menzil, yüksek hız
- **Kısıtlar**: İniş pisti gerekir, dağlık arazide sınırlı

#### Drone (İHA)
- **Menzil**: 50 km
- **Hız**: 80 km/h
- **Avantajlar**: Keşif ve gözlem, düşük maliyet
- **Kısıtlar**: Kısa menzil, düşük yük kapasitesi

## Skorlama Sistemi

### Değerlendirme Faktörleri

1. **Mesafe (0-40 puan)**: Hava üssüne olan uzaklık
2. **Rakım (0-20 puan)**: Yüksek rakım (>1500m) zorluk yaratır
3. **Arazi Tipi (0-15 puan)**: Dağlık ve ormanlık araziler daha zor
4. **Bitki Örtüsü (0-15 puan)**: Yoğun örtü iniş zorlaştırır
5. **Su Kaynağı Yakınlığı (+5 puan bonus)**: Acil iniş avantajı

### Arazi Tipleri ve Zorlukları

| Arazi Tipi | Zorluk | Ceza |
|------------|--------|------|
| Düz (FLAT) | Kolay | 0 |
| Tepeli (HILLY) | Orta | -5 |
| Dağlık (MOUNTAINOUS) | Zor | -15 |
| Ormanlık (FOREST) | Zor | -10 |
| Su Üzeri (WATER) | Kolay | +5 |

## API Kullanımı

### Tek Nokta Değerlendirmesi

```bash
POST /api/air-accessibility/classify
```

**İstek Örneği:**
```json
{
  "latitude": 38.4192,
  "longitude": 27.1287,
  "elevation": 150,
  "terrain_type": "HILLY",
  "vegetation_density": 0.6,
  "aircraft_type": "HELICOPTER"
}
```

**Yanıt Örneği:**
```json
{
  "accessibility_level": "GOOD",
  "score": 75.5,
  "distance_to_base_km": 45.2,
  "nearest_base": "Adnan Menderes Havalimanı",
  "eta_minutes": 12.3,
  "aircraft_type": "HELICOPTER",
  "terrain_type": "HILLY",
  "elevation_m": 150,
  "vegetation_density": 0.6,
  "reasons": ["Optimal koşullar"],
  "recommendations": ["Standart yaklaşım uygulanabilir"],
  "nearest_water_source": "Tahtalı Barajı",
  "water_distance_km": 3.5
}
```

### Toplu Değerlendirme

```bash
POST /api/air-accessibility/batch-classify
```

Birden fazla lokasyon için aynı anda değerlendirme yapar (max 1000 nokta).

### Grid Harita

```bash
POST /api/air-accessibility/grid-map
```

Belirli bir bölge için grid tabanlı erişilebilirlik haritası oluşturur (GeoJSON çıktısı).

**İstek Örneği:**
```json
{
  "min_lon": 26.8,
  "min_lat": 38.2,
  "max_lon": 27.3,
  "max_lat": 38.6,
  "grid_size": 0.02,
  "aircraft_type": "HELICOPTER"
}
```

### Hızlı Değerlendirme

```bash
GET /api/air-accessibility/quick-assess?lat=38.42&lon=27.13&aircraft=HELICOPTER
```

Minimal parametrelerle hızlı değerlendirme.

### Bilgi Endpointleri

- `GET /api/air-accessibility/air-bases` - Hava üsleri listesi
- `GET /api/air-accessibility/accessibility-levels` - Erişilebilirlik seviyeleri ve açıklamaları
- `GET /api/air-accessibility/aircraft-types` - Desteklenen hava araçları ve özellikleri
- `GET /api/air-accessibility/terrain-types` - Arazi tipleri ve zorlukları

## Harita Entegrasyonu

### Frontend Kullanımı

1. **Katman Gösterme**: "🚁 Hava Erişimi" butonuna tıklayın
2. **İnteraktif Harita**: Grid noktalarına tıklayarak detaylı bilgi alın
3. **Renkli Gösterim**: Her nokta erişilebilirlik seviyesine göre renklendirilir
4. **Legend**: Haritada otomatik olarak legend gösterilir

### Renk Şeması

- 🟢 **Yeşil** (#2ecc71): EXCELLENT
- 🔵 **Mavi** (#3498db): GOOD
- 🟠 **Turuncu** (#f39c12): MODERATE
- 🔴 **Kırmızı** (#e74c3c): DIFFICULT
- ⚫ **Koyu Kırmızı** (#8b0000): RESTRICTED

## Test

Test scripti çalıştırma:

```bash
python3 test_air_accessibility.py
```

Bu script şunları test eder:
- Farklı arazi tiplerinde değerlendirme
- Tüm hava aracı tipleri için karşılaştırma
- Toplu değerlendirme
- İstatistiksel analiz

## İzmir Bölgesi Hava Üsleri

1. **Adnan Menderes Havalimanı**
   - Konum: 38.2924°N, 27.1570°E
   - Tip: Sivil havalimanı

2. **Çiğli Hava Üssü**
   - Konum: 38.5130°N, 27.0100°E
   - Tip: Askeri hava üssü

3. **İzmir Körfez Heliport**
   - Konum: 38.4192°N, 27.1287°E
   - Tip: Heliport

## Dosya Yapısı

```
app/
├── services/
│   └── air_accessibility_service.py    # Ana servis mantığı
├── api/routers/
│   └── air_accessibility.py            # API endpoint'leri
├── schemas/
│   └── air_accessibility.py            # Pydantic şemaları
static/
├── index.html                          # Frontend entegrasyonu
└── data/
    ├── barajlar.geojson               # Barajlar (iniş noktası)
    ├── ponds-lakes.geojson            # Göl ve göletler
    └── water-reservoirs.geojson        # Su rezervuarları
test_air_accessibility.py               # Test scripti
```

## Kullanım Senaryoları

### 1. Yangın Müdahale Planlaması
Yüksek riskli bölgeler için hava desteği gereksinimini değerlendirin.

### 2. Kaynak Optimizasyonu
En erişilebilir bölgelere öncelik verin, zor erişim için alternatif planlar yapın.

### 3. Acil Durum Rotaları
Hava araçları için optimal rota ve iniş noktalarını belirleyin.

### 4. Eğitim ve Tatbikat
Pilotlar için zorluk seviyelerine göre senaryolar oluşturun.

## Geliştirme Notları

### Gelecek İyileştirmeler
- [ ] Rüzgar verisi entegrasyonu
- [ ] Hava durumu faktörleri (sis, yağış)
- [ ] Dinamik hava üssü ekleme/çıkarma
- [ ] Gerçek zamanlı hava trafik entegrasyonu
- [ ] 3D arazi modeli kullanımı
- [ ] Gece uçuş kısıtlamaları

### Performans Optimizasyonu
- Grid hesaplamaları önbelleğe alınabilir
- Büyük bölgeler için paralel işleme
- WebSocket ile gerçek zamanlı güncellemeler

## Lisans

KORU Projesi - İzmir Büyükşehir Belediyesi Bilgi İşlem Daire Başkanlığı

## İletişim

- **Telefon**: 153
- **Faks**: (0232) 293 39 95
- **E-Posta**: him@izmir.bel.tr

---

**Not**: Bu sistem LLF-2.3 kapsamında geliştirilmiştir ve yangın risk yönetimi için kritik bir araçtır.
