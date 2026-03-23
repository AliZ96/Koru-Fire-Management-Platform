# Push Edilecek Değişiklikler - Görev Mapping

## 1. Visualize risk zones for demo presentation (Başak)

| Dosya | Sınıf/Fonksiyon | Satır | Değişiklik Tipi | Açıklama |
|-------|-----------------|-------|-----------------|----------|
| static/index.html | getFireRiskColor() | 1029-1038 | Yeni Fonksiyon | Risk sınıflarına göre renk mapping |
| static/index.html | getFireRiskLabel() | 1039-1048 | Yeni Fonksiyon | Türkçe risk etiketi mapping |
| static/index.html | loadFireRiskPoints() | 1049-1173 | Yeni Fonksiyon | Risk noktalarını haritaya yükleme |
| static/index.html | loadFireRiskPoints() | 1089-1115 | İç Kod | CircleMarker görselleştirmesi |
| static/index.html | loadFireRiskPoints() | 1117-1124 | İç Kod | Popup tanımı |
| static/index.html | loadFireRiskPoints() | 1127-1143 | İç Kod | Legend ekleme |
| static/index.html | loadHeatmapGrid() | 1175-1286 | Yeni Fonksiyon | Heatmap grid yükleme |
| static/index.html | loadHeatmapGrid() | 1210-1235 | İç Kod | Poligon styling |
| static/index.html | btnFireRisk | 118 | Yeni Element | "Riskli Bölgeler" butonu |
| static/index.html | toggleFireRisk() | 1297-1312 | Yeni Fonksiyon | Toggle mekanizması |
| static/index.html | listeners | 1491 | Yeni Listener | Button click event |

---

## 2. Validate GIS risk layer visualization (Sena)

| Dosya | Sınıf/Fonksiyon | Satır | Değişiklik Tipi | Açıklama |
|-------|-----------------|-------|-----------------|----------|
| static/index.html | loadFireRiskPoints() | 1056-1059 | Validasyon Kodu | Response status ve format kontrolü |
| static/index.html | loadFireRiskPoints() | 1060-1067 | Validasyon Kodu | İzmir sınırları filtresi |
| static/index.html | loadFireRiskPoints() | 1069-1087 | Sıralama Logiki | Risk seviyesine göre feature sıralaması |
| static/index.html | loadFireRiskPoints() | 1117-1124 | Validasyon Kodu | Popup bilgileri doğruluğu |
| static/index.html | loadFireRiskPoints() | 1138-1141 | Sayım Logiki | Legend kategorileri sayısı |
| static/index.html | loadHeatmapGrid() | 1210-1235 | Validasyon Kodu | Grid hücre renk eşleştirmesi |
| static/index.html | loadFireRiskPoints() | 1247-1255 | Error Handling | Try-catch ve logging |

---

## 3. Integrate ML risk outputs with GIS risk layer (Sena)

| Dosya | Sınıf/Fonksiyon | Satır | Değişiklik Tipi | Açıklama |
|-------|-----------------|-------|-----------------|----------|
| app/api/routers/fire_risk.py | - | 1 | Yeni Dosya | Router oluşturuldu |
| app/api/routers/fire_risk.py | - | 11-12 | Konstant | RISK_DATA_PATH tanımı |
| app/api/routers/fire_risk.py | - | 14-18 | Konstant | RISK_COLORS mapping |
| app/api/routers/fire_risk.py | load_risk_data() | 20-24 | Yeni Fonksiyon | CSV veri yükleme |
| app/api/routers/fire_risk.py | get_fire_risk_points() | 26-69 | Yeni Endpoint | /api/fire-risk/points GET |
| app/api/routers/fire_risk.py | get_risk_statistics() | 71-91 | Yeni Endpoint | /api/fire-risk/statistics GET |
| app/api/routers/fire_risk.py | get_heatmap_data() | 93-172 | Yeni Endpoint | /api/fire-risk/heatmap-data GET |
| app/main.py | - | 10 | Import Ekleme | fire_risk_router import |
| app/main.py | create_app() | 34 | Router Ekleme | fire_risk_router.include_router() |
| static/index.html | loadFireRiskPoints() | 1055 | API Çağrısı | /api/fire-risk/points fetch |
| static/index.html | loadHeatmapGrid() | 1186 | API Çağrısı | /api/fire-risk/heatmap-data fetch |
| static/index.html | toggleFireRisk() | 1297-1312 | Toggle Logiki | Fire risk layer açıp kapatma |

---

## 4. Validate and test risk zones API responses (Sena)

| Dosya | Sınıf/Fonksiyon | Satır | Değişiklik Tipi | Açıklama |
|-------|-----------------|-------|-----------------|----------|
| app/api/routers/fire_risk.py | get_fire_risk_points() | 29-31 | Endpoint Parametreleri | risk_class, limit params |
| app/api/routers/fire_risk.py | get_fire_risk_points() | 32-69 | Response Format | GeoJSON FeatureCollection |
| app/api/routers/fire_risk.py | get_risk_statistics() | 80-89 | Response Format | İstatistik JSON format |
| app/api/routers/fire_risk.py | get_heatmap_data() | 103-172 | Response Format | Grid Polygon GeoJSON format |
| app/api/routers/fire_risk.py | get_heatmap_data() | 107-113 | Grid Logiki | Grid oluşturma ve gruplama |
| app/api/routers/fire_risk.py | get_heatmap_data() | 115-119 | Aggregation | Ortalama ve mode hesabı |
| app/api/routers/fire_risk.py | get_heatmap_data() | 125-132 | Koordinat Hesabı | Kare poligon oluşturma |
| app/api/routers/fire_risk.py | get_heatmap_data() | 135-145 | Renk Mapping | Risk skoruna göre renk |
| static/index.html | loadFireRiskPoints() | 1056 | Test | HTTP status validasyonu |
| static/index.html | loadFireRiskPoints() | 1057 | Test | JSON parsing |
| static/index.html | loadFireRiskPoints() | 1058-1060 | Test | Features validasyonu |
| static/index.html | loadFireRiskPoints() | 1062-1067 | Test | Koordinat validasyonu |
| static/index.html | loadFireRiskPoints() | 1247-1255 | Test | Error handling ve logging |

---

## Özet

### Oluşturulan Dosyalar (1)
1. **app/api/routers/fire_risk.py** (172 satır)
   - Router sınıfı (FastAPI)
   - 3 GET endpoint
   - İç fonksiyonlar: load_risk_data()

### Modifiye Edilen Dosyalar (2)
1. **app/main.py**
   - Import: fire_risk_router
   - include_router() çağrısı

2. **static/index.html**
   - 5 Yeni Fonksiyon
   - 1 Yeni Button Element
   - 1 Yeni Event Listener

### Toplam Değişiklik
- **Backend**: 1 yeni dosya + 2 modifiye
- **Frontend**: 1 modifiye
- **Yeni Endpoint**: 3 (/points, /statistics, /heatmap-data)
- **Yeni Fonksiyon**: 6 (Python 1, JavaScript 5)
- **Satır Ekleme**: ~400+ satır
