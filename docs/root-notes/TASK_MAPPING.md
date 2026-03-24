# Görevlere Karşılık Gelen Kod Değişiklikleri

## 1. "Visualize risk zones for demo presentation" (Başak)

Harita üzerinde risk bölgelerinin görsel olarak gösterilmesi için yapılan değişiklikler:

### Frontend (static/index.html)

#### Risk Noktaları Gösterimi
- **Button**: `line 118` - "Riskli Bölgeler" butonu eklendi
- **Renk Tanımı**: `line 1029-1038` - `getFireRiskColor()` fonksiyonu
- **Türkçe Etiketler**: `line 1039-1048` - `getFireRiskLabel()` fonksiyonu
- **Veri Yükleme**: `line 1049-1173` - `loadFireRiskPoints()` fonksiyonu

#### CircleMarker Görselleştirmesi
- `line 1089-1115` - GeoJSON'u CircleMarker'a çevirme
  - HIGH_RISK: Radius=8, opacity=1, fillOpacity=0.85
  - MEDIUM_RISK: Radius=6, opacity=0.9, fillOpacity=0.75
  - LOW_RISK: Radius=4, opacity=0.7, fillOpacity=0.6
  - SAFE_UNBURNABLE: Radius=3, opacity=0.5, fillOpacity=0.4

#### Popup Detayları
- `line 1117-1124` - Her noktada tıklandığında gösterilen popup:
  - Yangın Risk Analizi başlığı
  - Risk Sınıfı
  - Yangın Olasılığı (%)
  - Risk Skoru
  - Koordinatlar

#### Legend Eklenmesi
- `line 1127-1143` - Risk kategorileri ve sayıları gösteren legend
  - Yüksek Risk (Koyu Kırmızı)
  - Orta Risk (Kırmızı)
  - Düşük Risk (Turuncu)
  - Güvenli (Yeşil)

#### Heatmap Grid Görselleştirmesi
- `line 1175-1286` - `loadHeatmapGrid()` fonksiyonu
- `line 1210-1235` - Poligon stillendirmesi (risk skoruna göre renk)
  - 0.8+: #8b0000 (Koyu Kırmızı)
  - 0.6+: #d70000 (Kırmızı)
  - 0.4+: #ff4500 (Turuncu-Kırmızı)
  - 0.2+: #ffa500 (Turuncu)
  - <0.2: #ffff00 (Sarı)

---

## 2. "Validate GIS risk layer visualization" (Sena)

GIS risk layer'ın doğru şekilde görselleştirilmesinin doğrulanması:

### Frontend Doğrulamaları (static/index.html)

#### Veri Integritesi Kontrolü
- `line 1056-1059` - API response validasyonu
  ```javascript
  if (!response.ok) throw new Error('API hatası: ' + response.status);
  const geoJson = await response.json();
  if (!geoJson.features || geoJson.features.length === 0)
  ```

#### İzmir Sınırları Filtresi
- `line 1060-1067` - Bölge geçerliliği kontrolü
  ```javascript
  const filteredFeatures = geoJson.features.filter(f => {
    const coords = f.geometry?.coordinates;
    if (!coords || coords.length < 2) return false;
    const [lon, lat] = coords;
    return isInIzmir(lat, lon);  // Doğrulama
  });
  ```

#### Feature Sıralaması
- `line 1069-1087` - Risk seviyesine göre özellik sıralaması
  - Düşük riskler ilk (arka planda)
  - Orta riskler ortada
  - Yüksek riskler üstte (ön planda)

#### Popup Doğruluğu
- `line 1117-1124` - Tüm gerekli bilgilerin gösterilmesi
  - Risk Sınıfı (Türkçe)
  - Fire Probability (yüzdeye çevrilmiş)
  - Combined Risk Score (4 ondalık)
  - Koordinatlar (4 ondalık)

#### Legend Sayı Doğruluğu
- `line 1138-1141` - Her kategori için doğru sayım
  ```javascript
  div.innerHTML = ... highRiskFeatures.length ... mediumRiskFeatures.length ...
  ```

#### Heatmap Grid Styling
- `line 1210-1235` - Risk skoruna göre doğru renk eşleştirmesi
- `line 1237-1260` - Poligon popup'ı (grid hücre detayları)

#### Hata Yönetimi
- `line 1247-1255` - Try-catch ve error logging
  ```javascript
  try { ... } catch (e) { 
    info.textContent = 'Yangın risk yükleme hatası: ' + e.message;
    console.error('Yangın risk yükleme hatası:', e);
  }
  ```

---

## 3. "Integrate ML risk outputs with GIS risk layer" (Sena)

ML modeli tahminlerinin GIS risk layer ile entegrasyonu:

### Backend Geliştirmeleri

#### fire_risk.py Router Oluşturulması
- **File**: `app/api/routers/fire_risk.py` (yeni dosya)
- `line 1-8` - Import'lar ve router tanımı

#### ML Veri Kaynağı Tanımı
- `line 11-12` - CSV dosya yolu
  ```python
  RISK_DATA_PATH = Path(__file__).parent.parent.parent.parent / "database" / "ml-map" / "izmir_future_fire_risk_dataset.csv"
  ```

#### Risk Renklendirmesi Mapping'i
- `line 14-18` - RISK_COLORS dictionary
  - SAFE_UNBURNABLE: #2ecc71 (Yeşil)
  - LOW_RISK: #f39c12 (Turuncu)
  - MEDIUM_RISK: #e74c3c (Kırmızı)
  - HIGH_RISK: #8b0000 (Koyu Kırmızı)

#### CSV Veri Yüklemesi
- `line 20-24` - `load_risk_data()` fonksiyonu

#### API Endpoint: /api/fire-risk/points
- `line 26-69` - GET /points endpoint
  - risk_class filtresi (opsiyonel)
  - limit parametresi (default: 50000)
  - GeoJSON FeatureCollection dönüş

#### API Endpoint: /api/fire-risk/statistics
- `line 71-91` - GET /statistics endpoint
  - Risk dağılımı
  - Ortalama olasılık
  - Risk skoru ortalaması
  - Kategori bazlı sayımlar

#### API Endpoint: /api/fire-risk/heatmap-data
- `line 93-172` - GET /heatmap-data endpoint
  - Grid oluşturma (cell_size parametresi)
  - Poligon koordinatlarının hesaplanması
  - Risk skoruna göre renk atama

#### main.py'ye Entegrasyon
- `app/main.py` `line 10` - Import
  ```python
  from app.api.routers.fire_risk import router as fire_risk_router
  ```
- `app/main.py` `line 34` - Router include
  ```python
  app.include_router(fire_risk_router)
  ```

### Frontend Entegrasyonu

#### API Çağrısı
- `static/index.html` `line 1055` - Fire risk points API çağrısı
  ```javascript
  const response = await fetch('/api/fire-risk/points?limit=50000');
  ```

#### API Çağrısı (Heatmap)
- `static/index.html` `line 1186` - Heatmap data API çağrısı
  ```javascript
  const response = await fetch('/api/fire-risk/heatmap-data?cell_size=0.05');
  ```

#### Toggle Mekanizması
- `static/index.html` `line 1297-1312` - `toggleFireRisk()` fonksiyonu
- `static/index.html` `line 1491` - Button event listener
  ```javascript
  document.getElementById('btnFireRisk').addEventListener('click', toggleFireRisk);
  ```

---

## 4. "Validate and test risk zones API responses" (Sena)

API endpoint'lerinin doğru yanıtlar döndürmesinin test ve doğrulanması:

### GET /api/fire-risk/points

#### Request Parametreleri
- `app/api/routers/fire_risk.py` `line 29-31`
  - `risk_class` (opsiyonel): Filter
  - `limit` (default: 50000): Sayı limiti

#### Response Format
- `line 32-69` - GeoJSON FeatureCollection
  ```json
  {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {
          "type": "Point",
          "coordinates": [longitude, latitude]
        },
        "properties": {
          "risk_class": "HIGH_RISK|MEDIUM_RISK|LOW_RISK|SAFE_UNBURNABLE",
          "fire_probability": 0.0-1.0,
          "high_fire_probability": 0.0-1.0,
          "combined_risk_score": 0.0-1.0,
          "color": "#HEX"
        }
      }
    ],
    "total": number
  }
  ```

#### Frontend Validasyonu
- `static/index.html` `line 1056-1059` - Response status ve format kontrolü
- `static/index.html` `line 1073-1075` - Console logging

### GET /api/fire-risk/statistics

#### Response Format
- `app/api/routers/fire_risk.py` `line 80-89`
  ```json
  {
    "total_points": number,
    "risk_distribution": {
      "SAFE_UNBURNABLE": number,
      "LOW_RISK": number,
      "MEDIUM_RISK": number,
      "HIGH_RISK": number
    },
    "average_fire_probability": 0.0-1.0,
    "average_combined_risk_score": 0.0-1.0,
    "high_risk_count": number,
    "medium_risk_count": number,
    "low_risk_count": number,
    "safe_count": number
  }
  ```

### GET /api/fire-risk/heatmap-data

#### Request Parametreleri
- `app/api/routers/fire_risk.py` `line 100` - `cell_size` (default: 0.05°)

#### Response Format
- `line 103-172` - GeoJSON FeatureCollection (Polygon'lar)
  ```json
  {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {
          "type": "Polygon",
          "coordinates": [[[lon, lat], ...]]
        },
        "properties": {
          "combined_risk_score": 0.0-1.0,
          "fire_probability": 0.0-1.0,
          "risk_class": "HIGH_RISK|MEDIUM_RISK|...",
          "color": "#HEX"
        }
      }
    ],
    "total_cells": number,
    "cell_size": 0.05
  }
  ```

#### Grid Hesaplama Logiki
- `line 107-113` - Grid oluşturma ve gruplama
  - Latitude/longitude'u cell_size'a göre böl
  - Aynı grid hücresindeki verileri birleştir

- `line 115-119` - Aggregation
  - combined_risk_score: Ortalama
  - fire_probability: Ortalama
  - predicted_risk_class: Mode (en sık sınıf)

#### Poligon Koordinat Hesabı
- `line 125-132` - Kare poligon oluşturma
  ```python
  half_size = cell_size / 2
  coordinates = [[
    [lon - half_size, lat - half_size],
    [lon + half_size, lat - half_size],
    [lon + half_size, lat + half_size],
    [lon - half_size, lat + half_size],
    [lon - half_size, lat - half_size]
  ]]
  ```

#### Renk Eşleştirmesi
- `line 135-145` - Risk skoruna göre renk
  - 0.8+: #8b0000
  - 0.6+: #d70000
  - 0.4+: #ff4500
  - 0.2+: #ffa500
  - <0.2: #ffff00

### Frontend Test Validasyonları

#### Response Status Kontrolü
- `static/index.html` `line 1056` - HTTP status kodu
  ```javascript
  if (!response.ok) throw new Error('API hatası: ' + response.status);
  ```

#### Response Parsing
- `static/index.html` `line 1057` - JSON parsing
  ```javascript
  const geoJson = await response.json();
  ```

#### Feature Validasyonu
- `static/index.html` `line 1058-1060` - Features varlığı ve doluluk kontrolü
  ```javascript
  if (!geoJson.features || geoJson.features.length === 0) {
    info.textContent = 'Yangın risk verisi bulunamadı';
    return;
  }
  ```

#### Koordinat Validasyonu
- `static/index.html` `line 1062-1067` - Geometry kontrol
  ```javascript
  const coords = f.geometry?.coordinates;
  if (!coords || coords.length < 2) return false;
  ```

#### Error Handling
- `static/index.html` `line 1247-1255` - Try-catch bloku
  ```javascript
  try { ... } catch (e) {
    console.error('Yangın risk yükleme hatası:', e);
  }
  ```

---

## Dosya Özeti

### Oluşturulan Dosyalar
- `app/api/routers/fire_risk.py` (172 satır) - Tüm API endpoint'lerini içerir

### Modifiye Edilen Dosyalar
- `app/main.py` - fire_risk_router import ve include (2 satır ekleme)
- `static/index.html` - UI ve visualisasyon fonksiyonları (~250 satır ekleme)

### Kullanılan Veri Dosyası
- `database/ml-map/izmir_future_fire_risk_dataset.csv` - ML tahminleri

---

## Teknoloji Stack

### Backend
- **Framework**: FastAPI
- **Veri İşleme**: Pandas
- **Format**: GeoJSON

### Frontend
- **Map Library**: Leaflet.js
- **Görselleştirme**: CircleMarker, Polygon
- **Stil**: CSS

### Veri Kaynağı
- **ML Model Output**: izmir_future_fire_risk_dataset.csv
- **Columns**: latitude, longitude, predicted_risk_class, fire_probability, high_fire_probability, combined_risk_score
