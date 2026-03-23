# SCRUM-58: Resource Proximity API Reference

## 📡 Endpoint: `/api/proximity/high-medium-grid`

### HTTP Method
```
GET /api/proximity/high-medium-grid
```

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `cell_size` | float | No | 0.02 | Grid hücresi boyutu (degrees) |
| `min_lat` | float | No | null | Minimum enlem filtresi |
| `min_lon` | float | No | null | Minimum boylam filtresi |
| `max_lat` | float | No | null | Maksimum enlem filtresi |
| `max_lon` | float | No | null | Maksimum boylam filtresi |

### Request Examples

#### 1️⃣ Temel Request (Tüm İzmir)
```bash
curl -X GET "http://localhost:8000/api/proximity/high-medium-grid" \
  -H "Content-Type: application/json"
```

#### 2️⃣ Custom Cell Size
```bash
curl -X GET "http://localhost:8000/api/proximity/high-medium-grid?cell_size=0.01" \
  -H "Content-Type: application/json"
```

#### 3️⃣ Bölge Filtresi (Alsancak)
```bash
curl -X GET "http://localhost:8000/api/proximity/high-medium-grid?min_lat=38.42&max_lat=38.44&min_lon=27.12&max_lon=27.15" \
  -H "Content-Type: application/json"
```

### Response Format

#### HTTP Status: 200 OK

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [27.1200, 38.5000],
            [27.1400, 38.5000],
            [27.1400, 38.5200],
            [27.1200, 38.5200],
            [27.1200, 38.5000]
          ]
        ]
      },
      "properties": {
        "center_lat": 38.5100,
        "center_lon": 27.1300,
        "risk_class": "HIGH_RISK",
        "combined_risk_score": 0.8540,
        "point_count": 42,
        "nearest_water_id": "Tahtalı Barajı",
        "nearest_water_distance": 12.345,
        "nearest_water_lat": 38.4890,
        "nearest_water_lon": 27.0890,
        "nearest_station_id": "Konak İtfaiye Grubu",
        "nearest_station_distance": 8.234,
        "nearest_station_lat": 38.4192,
        "nearest_station_lon": 27.1287,
        "validation_notes": null
      }
    },
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [...]
      },
      "properties": {...}
    }
  ],
  "total_cells": 156,
  "cell_size": 0.02,
  "distance_metric": "haversine_km",
  "schema_version": "scrum58_finalized"
}
```

---

## 🔍 Response Fields Açıklama

### Geometri (Geometry)

| Alan | Tip | Açıklama |
|------|-----|----------|
| `type` | string | "Polygon" (her zaman kare grid hücresi) |
| `coordinates` | array | [lon, lat] çiftleri (GeoJSON standardı) |

### Özellikleri (Properties)

#### Grid Bilgileri
- **`center_lat`** (float): Hücre merkezi enlemi (4 decimal, ±11m)
- **`center_lon`** (float): Hücre merkezi boylamı (4 decimal, ±11m)
- **`risk_class`** (string): "HIGH_RISK" | "MEDIUM_RISK"
- **`combined_risk_score`** (float): 0.0-1.0 arası risk skoru
- **`point_count`** (int): Bu hücrede kaç fire risk point var

#### Su Kaynağı Eşleşmesi (Water Resource Mapping)
- **`nearest_water_id`** (string): Su kaynağının adı
  - Örn: "Tahtalı Barajı", "Ali Paşa Şadırvanı"
- **`nearest_water_distance`** (float): Haversine mesafesi (km, 3 decimal)
  - Örn: 12.345 (= 12.345 km)
- **`nearest_water_lat`** (float): Su kaynağı enlemi (4 decimal)
- **`nearest_water_lon`** (float): Su kaynağı boylamı (4 decimal)

#### İtfaiye İstasyonu Eşleşmesi (Fire Station Mapping)
- **`nearest_station_id`** (string): İtfaiye istasyonunun adı
  - Örn: "Konak İtfaiye Grubu", "Çiğli İtfaiye Grubu"
- **`nearest_station_distance`** (float): Haversine mesafesi (km, 3 decimal)
- **`nearest_station_lat`** (float): İstasyon enlemi (4 decimal)
- **`nearest_station_lon`** (float): İstasyon boylamı (4 decimal)

#### Validasyon
- **`validation_notes`** (string || null): Doğrulama notları ve uyarılar
  - null = Hata yok
  - "Su kaynağı bulunamadı" = Kaynak problemi var

### Metadata
- **`type`**: "FeatureCollection" (GeoJSON standard)
- **`total_cells`**: Toplam grid hücresi sayısı
- **`cell_size`**: Query'de kullanılan hücre boyutu (degrees)
- **`distance_metric`**: "haversine_km" (SCRUM-58 standardı)
- **`schema_version`**: "scrum58_finalized"

---

## 📊 Kullanım Örnekleri

### 1️⃣ Harita Katmanı Olarak Gösterme (Frontend)

```javascript
// Tüm grid hücrelerini haritaya yükle
fetch('/api/proximity/high-medium-grid')
  .then(res => res.json())
  .then(geojson => {
    L.geoJSON(geojson, {
      style: (feature) => {
        const riskClass = feature.properties.risk_class;
        return {
          color: riskClass === 'HIGH_RISK' ? '#ff0000' : '#ff8800',
          opacity: 0.7,
          fillOpacity: 0.5
        };
      },
      onEachFeature: (feature, layer) => {
        const props = feature.properties;
        const popup = `
          <b>Risk Grid Cell</b><br>
          Risk Class: ${props.risk_class}<br>
          Score: ${props.combined_risk_score.toFixed(3)}<br>
          <hr>
          <b>Nearest Water:</b><br>
          ${props.nearest_water_id} (${props.nearest_water_distance} km)<br>
          <b>Nearest Station:</b><br>
          ${props.nearest_station_id} (${props.nearest_station_distance} km)
        `;
        layer.bindPopup(popup);
      }
    }).addTo(map);
  });
```

### 2️⃣ CSV Export (Rapor Oluşturma)

```python
import requests
import pandas as pd

# API çağrısı
response = requests.get('http://localhost:8000/api/proximity/high-medium-grid')
geojson = response.json()

# Feature'ları DataFrame'e çevir
rows = []
for feature in geojson['features']:
    props = feature['properties']
    rows.append({
        'risk_class': props['risk_class'],
        'combined_risk_score': props['combined_risk_score'],
        'point_count': props['point_count'],
        'nearest_water': props['nearest_water_id'],
        'water_distance_km': props['nearest_water_distance'],
        'nearest_station': props['nearest_station_id'],
        'station_distance_km': props['nearest_station_distance'],
    })

df = pd.DataFrame(rows)
df.to_csv('risk_zones_with_resources.csv', index=False)
```

### 3️⃣ Bölge Analizi (Region-specific Query)

```bash
# Alsancak bölgesi (HIGH_RISK yoğun)
curl "http://localhost:8000/api/proximity/high-medium-grid?min_lat=38.42&max_lat=38.44&min_lon=27.12&max_lon=27.15" \
  -o alsancak_risk_grid.geojson
```

---

## 🔬 Response Örnekleri

### Örnek 1: HIGH_RISK Hücresi (Body Kıyısı)

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[27.1400, 38.5000], [27.1600, 38.5000], [27.1600, 38.5200], [27.1400, 38.5200], [27.1400, 38.5000]]]
  },
  "properties": {
    "center_lat": 38.5100,
    "center_lon": 27.1500,
    "risk_class": "HIGH_RISK",
    "combined_risk_score": 0.8540,
    "point_count": 42,
    "nearest_water_id": "Tahtalı Barajı",
    "nearest_water_distance": 12.345,
    "nearest_water_lat": 38.4890,
    "nearest_water_lon": 27.0890,
    "nearest_station_id": "Konak İtfaiye Grubu",
    "nearest_station_distance": 8.234,
    "nearest_station_lat": 38.4192,
    "nearest_station_lon": 27.1287,
    "validation_notes": null
  }
}
```

### Örnek 2: MEDIUM_RISK Hücresi (Ufuk Çizgisi)

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[27.1200, 38.4800], [27.1400, 38.4800], [27.1400, 38.5000], [27.1200, 38.5000], [27.1200, 38.4800]]]
  },
  "properties": {
    "center_lat": 38.4900,
    "center_lon": 27.1300,
    "risk_class": "MEDIUM_RISK",
    "combined_risk_score": 0.6120,
    "point_count": 28,
    "nearest_water_id": "Alsancak Su Deposu",
    "nearest_water_distance": 5.678,
    "nearest_water_lat": 38.4890,
    "nearest_water_lon": 27.1320,
    "nearest_station_id": "Gaziemir İtfaiye Grubu",
    "nearest_station_distance": 15.234,
    "nearest_station_lat": 38.2924,
    "nearest_station_lon": 27.1570,
    "validation_notes": null
  }
}
```

---

## ⚠️ Hata Yönetimi

### HTTP 400 - Bad Request
```json
{
  "detail": "Invalid cell_size: must be positive"
}
```

#### Sebepler:
- `cell_size <= 0`
- `min_lat > max_lat`
- `min_lon > max_lon`

### HTTP 500 - Internal Server Error
```json
{
  "detail": "Failed to load risk data"
}
```

#### Sebepler:
- CSV dosyası bulunamadı
- GeoJSON parse hatası
- Memory/performance issue

---

## 🚀 Performance & Limits

| Metrik | Değer | Not |
|--------|-------|-----|
| **Response Time** | <100ms | İzmir full grid for default cell_size |
| **Max cell_size** | 1.0 | Çok büyük hücreler |
| **Min cell_size** | 0.001 | Çok detaylı (yavaş) |
| **Default cell_size** | 0.02 | Balanced (~156 cells for İzmir) |
| **Typical cell count** | 100-500 | Bölge seçimine göre |

---

## 🔐 Güvenlik

### Rate Limiting
- No explicit rate limiting (internal API)
- Production'da: CloudFlare/API Gateway eklenmeli

### Input Validation
- ✅ Cell size > 0
- ✅ BBox coordinates valid
- ✅ Float precision check

### Data Privacy
- ✅ Tüm veriler public GeoJSON/OSM kaynakları
- Koordinatlar sensitive değil (entity locations public)

---

## 📚 İlgili Endpointler

| Endpoint | Amaç |
|----------|------|
| `/api/fire-risk/points` | Risk noktaları (raw) |
| `/api/fire-risk/heatmap-data` | Heatmap grid (alternative) |
| `/api/fire-risk/statistics` | Risk istatistikleri |
| `/api/proximity/high-medium-grid` | Kaynak eşlemesi (THIS) |

---

## 📖 Kaynaklar

- **SCRUM-58**: [SCRUM-58_RESOURCE_MAPPING_VALIDATION.md](./SCRUM-58_RESOURCE_MAPPING_VALIDATION.md)
- **Metodoloji**: Haversine Distance Formula
- **Veri**: OpenStreetMap (water-tank, fire-stations)
- **İzmir Bounds**: 26.5°E-27.5°E, 37.5°N-39.5°N

---

**Document Version**: 1.0  
**Schema Version**: scrum58_finalized  
**Last Updated**: February 27, 2026
