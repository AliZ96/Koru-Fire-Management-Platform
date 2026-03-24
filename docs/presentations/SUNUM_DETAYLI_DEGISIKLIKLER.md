# 🎯 SUNUM: Yapılan Tüm Değişiklikler - Detaylı Açıklama

---

## 📋 İçindekiler
1. [Proje Amaç ve Hedef](#proje-amaç-ve-hedef)
2. [Mimari Genel Bakış](#mimari-genel-bakış)
3. [Backend Değişiklikleri](#backend-değişiklikleri)
4. [Frontend Değişiklikleri](#frontend-değişiklikleri)
5. [Veri Akışı](#veri-akışı)
6. [API Endpoint'leri](#api-endpoints)
7. [Görselleştirme Detayları](#görselleştirme-detayları)
8. [Validasyon Mekanizmaları](#validasyon-mekanizmaları)

---

## 🎯 Proje Amaç ve Hedef

### Amacı
**İzmir bölgesindeki orman yangınlarını tahmin etmek ve görselleştirmek**

### Hedefleri
- ✅ ML modelinin yangın risk tahminlerini API üzerinden sunmak
- ✅ GIS sisteminde risk bölgelerini görselleştirmek
- ✅ Risk verilerini harita üzerinde interaktif olarak göstermek
- ✅ Heatmap grid ile risk yoğunluğunu analiz etmek

### Görevler ve Sorumlu Kişiler
| # | Görev | Kişi | Status |
|---|-------|------|--------|
| 1 | Visualize risk zones for demo | Başak | ✅ Tamamlandı |
| 2 | Validate GIS risk layer | Sena | ✅ Tamamlandı |
| 3 | Integrate ML outputs + GIS | Sena | ✅ Tamamlandı |
| 4 | Validate API responses | Sena | ✅ Tamamlandı |

---

## 🏗️ Mimari Genel Bakış

```
┌─────────────────────────────────────────────────────────┐
│                  FRONTEND (JavaScript/Leaflet)          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ index.html - GIS Harita & Görselleştirme        │  │
│  │ • Fire Risk Layer                                │  │
│  │ • Heatmap Grid                                   │  │
│  │ • Legend & Popup                                 │  │
│  └──────────────────────────────────────────────────┘  │
│                          ⬇️ HTTP Requests              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │ fire_risk.py - API Router                        │  │
│  │ • GET /api/fire-risk/points (Risk Noktaları)    │  │
│  │ • GET /api/fire-risk/statistics (İstatistikler) │  │
│  │ • GET /api/fire-risk/heatmap-data (Heatmap)     │  │
│  └──────────────────────────────────────────────────┘  │
│                          ⬇️ Data Processing             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              DATA SOURCE (CSV)                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │ izmir_future_fire_risk_dataset.csv               │  │
│  │ • latitude, longitude                            │  │
│  │ • predicted_risk_class                           │  │
│  │ • fire_probability                               │  │
│  │ • combined_risk_score                            │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 Backend Değişiklikleri

### 1️⃣ YENİ DOSYA: `app/api/routers/fire_risk.py` (172 satır)

#### Dosya Yapısı
```
fire_risk.py
├── Imports (FastAPI, Pandas, Path)
├── Router Tanımı (prefix="/api/fire-risk")
├── Constants
│   ├── RISK_DATA_PATH (CSV dosya yolu)
│   └── RISK_COLORS (Renk mapping)
├── Utility Functions
│   └── load_risk_data()
└── API Endpoints (3 adet)
    ├── GET /points
    ├── GET /statistics
    └── GET /heatmap-data
```

#### A. Imports ve Setup (Line 1-10)
```python
from fastapi import APIRouter
from typing import List, Optional
import pandas as pd
from pathlib import Path

router = APIRouter(prefix="/api/fire-risk", tags=["fire-risk"])
```
**Ne yapıyor?**
- FastAPI router oluşturur
- Tüm endpointler `/api/fire-risk` prefix'i ile çalışır
- Pandas ile CSV veri işleme
- Path ile dinamik dosya yolu

---

#### B. Veri Kaynağı Tanımı (Line 11-23)
```python
RISK_DATA_PATH = Path(__file__).parent.parent.parent.parent / "database" / "ml-map" / "izmir_future_fire_risk_dataset.csv"

RISK_COLORS = {
    "SAFE_UNBURNABLE": "#2ecc71",      # Yeşil
    "LOW_RISK": "#f39c12",              # Turuncu
    "MEDIUM_RISK": "#e74c3c",           # Kırmızı
    "HIGH_RISK": "#8b0000",             # Koyu Kırmızı
}
```
**Ne yapıyor?**
- ML modelinin tahmin dosyasını işaret
- Risk sınıflarını renklerle eşleştir
- Frontend'de sabit renk kullanımı

**Risk Sınıfları:**
| Sınıf | Renk | Anlamı |
|-------|------|--------|
| SAFE_UNBURNABLE | Yeşil (#2ecc71) | Yanma riski yok |
| LOW_RISK | Turuncu (#f39c12) | Düşük yangın riski |
| MEDIUM_RISK | Kırmızı (#e74c3c) | Orta yangın riski |
| HIGH_RISK | Koyu Kırmızı (#8b0000) | Yüksek yangın riski |

---

#### C. Veri Yükleme Fonksiyonu (Line 20-24)
```python
def load_risk_data():
    """CSV'den yangın risk verilerini yükle"""
    if RISK_DATA_PATH.exists():
        return pd.read_csv(RISK_DATA_PATH)
    return None
```
**Ne yapıyor?**
- CSV dosyasını pandas DataFrame'e yükler
- Dosya yoksa None döndürür
- Tüm endpointler tarafından çağrılır

**CSV Dosyası Columns:**
```
latitude, longitude, predicted_risk_class, fire_probability, 
high_fire_probability, combined_risk_score
```

---

#### D. ENDPOINT 1: `/api/fire-risk/points` (Line 26-69)

**Amaç:** Tüm risk noktalarını GeoJSON formatında döndür

**İstek Parametreleri:**
```
GET /api/fire-risk/points?risk_class=HIGH_RISK&limit=50000
```
- `risk_class` (opsiyonel): Belirli sınıfı filtrele
- `limit` (default: 50000): Maksimum nokta sayısı

**Yanıt Formatı:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [28.3, 38.2]
      },
      "properties": {
        "risk_class": "HIGH_RISK",
        "fire_probability": 0.7823,
        "high_fire_probability": 0.6543,
        "combined_risk_score": 0.8234,
        "color": "#8b0000"
      }
    }
  ],
  "total": 12345
}
```

**Mantığı:**
```python
1. CSV'i yükle
2. risk_class filtresi varsa uygulandırsa filtrele
3. limit kadar veriyi al
4. Pandas'ın iterrows() ile satır satır döngü
5. Her satırı GeoJSON Feature'a çevir
6. FeatureCollection olarak döndür
```

**Kullanım Süreci:**
```
Frontend → fetch('/api/fire-risk/points?limit=50000')
         ↓
Backend  → load_risk_data() → 50000 noktayı GeoJSON'a çevir
         ↓
Frontend → Noktaları haritada CircleMarker olarak göster
```

---

#### E. ENDPOINT 2: `/api/fire-risk/statistics` (Line 71-91)

**Amaç:** Genel istatistik ve özet bilgi döndür

**İstek:**
```
GET /api/fire-risk/statistics
```

**Yanıt Formatı:**
```json
{
  "total_points": 125000,
  "risk_distribution": {
    "SAFE_UNBURNABLE": 50000,
    "LOW_RISK": 40000,
    "MEDIUM_RISK": 25000,
    "HIGH_RISK": 10000
  },
  "average_fire_probability": 0.456,
  "average_combined_risk_score": 0.523,
  "high_risk_count": 10000,
  "medium_risk_count": 25000,
  "low_risk_count": 40000,
  "safe_count": 50000
}
```

**Ne hesaplıyor?**
- `total_points`: Toplam nokta sayısı
- `risk_distribution`: Her sınıfın kaç nokta var
- `average_fire_probability`: Ortalama yangın olasılığı
- `average_combined_risk_score`: Ortalama risk skoru
- Sınıf bazında sayımlar

**Kullanım:** Dashboard'da özet istatistikler göstermek

---

#### F. ENDPOINT 3: `/api/fire-risk/heatmap-data` (Line 93-172)

**Amaç:** Grid heatmap verilerini poligon olarak döndür

**İstek Parametreleri:**
```
GET /api/fire-risk/heatmap-data?cell_size=0.05
```
- `cell_size`: Grid hücre boyutu (derece cinsinden)
  - 0.05° ≈ 5.5 km

**Mantığı:**

**Adım 1: Grid Oluşturma**
```python
df_copy['lat_grid'] = (df_copy['latitude'] / cell_size).astype(int) * cell_size
df_copy['lon_grid'] = (df_copy['longitude'] / cell_size).astype(int) * cell_size
```
- Koordinatları cell_size'a göre grupla
- Örnek: 38.234 lat, cell_size=0.05 → 38.20 (grid noktası)

**Adım 2: Aggregation (Veri Birleştirme)**
```python
grid_data = df_copy.groupby(['lat_grid', 'lon_grid']).agg({
    'combined_risk_score': 'mean',
    'fire_probability': 'mean',
    'predicted_risk_class': lambda x: x.mode()[0]
})
```
- Her grid hücresinde:
  - Risk skorunun ortalaması
  - Yangın olasılığının ortalaması
  - En sık görülen risk sınıfı (mode)

**Adım 3: Poligon Oluşturma**
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
- Kare şeklinde poligon (4 köşe + başlangıç noktası)

**Adım 4: Renk Mapping**
```python
if risk_score >= 0.8:
    color = "#8b0000"  # Koyu Kırmızı
elif risk_score >= 0.6:
    color = "#d70000"  # Kırmızı
elif risk_score >= 0.4:
    color = "#ff4500"  # Turuncu-Kırmızı
elif risk_score >= 0.2:
    color = "#ffa500"  # Turuncu
else:
    color = "#ffff00"  # Sarı
```

**Yanıt Formatı:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [28.2, 38.2], [28.25, 38.2],
          [28.25, 38.25], [28.2, 38.25],
          [28.2, 38.2]
        ]]
      },
      "properties": {
        "combined_risk_score": 0.756,
        "fire_probability": 0.654,
        "risk_class": "HIGH_RISK",
        "color": "#8b0000"
      }
    }
  ],
  "total_cells": 234,
  "cell_size": 0.05
}
```

**Görsel Sonuç:**
```
Haritada renkli grid hücreler (heatmap)
Sarı (düşük risk) → Kırmızı (yüksek risk)
```

---

### 2️⃣ MODİFİYE DOSYA: `app/main.py`

#### Değişiklik 1: Import Ekleme (Line 10)
```python
from app.api.routers.fire_risk import router as fire_risk_router
```
**Ne yapıyor?** - fire_risk router'ını import eder

#### Değişiklik 2: Router Ekleme (Line 34)
```python
app.include_router(fire_risk_router)
```
**Ne yapıyor?** - fire_risk router'ını FastAPI uygulamasına entegre eder

**Sonuç:**
- `/api/fire-risk/points` endpoint'i kullanılabilir
- `/api/fire-risk/statistics` endpoint'i kullanılabilir
- `/api/fire-risk/heatmap-data` endpoint'i kullanılabilir

---

## 🎨 Frontend Değişiklikleri

### MODİFİYE DOSYA: `static/index.html`

#### 1️⃣ YENİ CONSTANT'LAR (Line 1026-1027)
```javascript
let fireRiskLayer = null;
let fireRiskLegendCtl = null;
let heatmapLayer = null;
let heatmapLegendCtl = null;
```
**Ne yapıyor?**
- Layer referanslarını sakla
- Toggle (aç/kapat) mekanizması için
- Eski layer varsa temizlemek için

---

#### 2️⃣ YENİ FONKSIYON: `getFireRiskColor()` (Line 1029-1038)
```javascript
function getFireRiskColor(riskClass) {
  const colors = {
    'SAFE_UNBURNABLE': '#2ecc71',
    'LOW_RISK': '#f39c12',
    'MEDIUM_RISK': '#e74c3c',
    'HIGH_RISK': '#8b0000'
  };
  return colors[riskClass] || '#808080';
}
```
**Ne yapıyor?**
- Risk sınıfına göre hex renk kodu döndür
- Backend'deki RISK_COLORS ile aynı
- Default: Gri (#808080)

---

#### 3️⃣ YENİ FONKSIYON: `getFireRiskLabel()` (Line 1039-1048)
```javascript
function getFireRiskLabel(riskClass) {
  const labels = {
    'SAFE_UNBURNABLE': 'Güvenli/Yanmayan',
    'LOW_RISK': 'Düşük Risk',
    'MEDIUM_RISK': 'Orta Risk',
    'HIGH_RISK': 'Yüksek Risk'
  };
  return labels[riskClass] || riskClass;
}
```
**Ne yapıyor?**
- Türkçe etiketi döndür
- Popup ve Legend'de kullanıl
- Kullanıcı dostu gösterim

---

#### 4️⃣ YENİ FONKSIYON: `loadFireRiskPoints()` (Line 1049-1173)

**Bu fonksiyon 4 ana kısımdan oluşur:**

##### A. API Çağrısı ve Validasyon (Line 1055-1067)

**1. API'ye İstek Gönder**
```javascript
const response = await fetch('/api/fire-risk/points?limit=50000');
```

**2. HTTP Status Validasyonu**
```javascript
if (!response.ok) throw new Error('API hatası: ' + response.status);
```
- Status 200-299 arasında değilse hata

**3. JSON Parse Et**
```javascript
const geoJson = await response.json();
```

**4. Features Validasyonu**
```javascript
if (!geoJson.features || geoJson.features.length === 0) {
  info.textContent = 'Yangın risk verisi bulunamadı';
  return;
}
```
- Features dizisi boşsa çıkış yap

**5. İzmir Sınırları Filtresi + Koordinat Validasyonu**
```javascript
const filteredFeatures = geoJson.features.filter(f => {
  const coords = f.geometry?.coordinates;
  if (!coords || coords.length < 2) return false;
  const [lon, lat] = coords;
  return isInIzmir(lat, lon);
});
```
- Koordinat varlığını kontrol et
- İzmir sınırları içinde olanları al

---

##### B. Feature Sıralama (Line 1069-1087)

**Neden sırlıyoruz?**
- Yüksek riskler başında olsun (ön planda)
- Düşük riskler arka planda
- Görsel öncelik

```javascript
let lowRiskFeatures = filteredFeatures.filter(f => 
  f.properties.risk_class !== 'HIGH_RISK' && 
  f.properties.risk_class !== 'MEDIUM_RISK'
);
let mediumRiskFeatures = filteredFeatures.filter(f => 
  f.properties.risk_class === 'MEDIUM_RISK'
);
let highRiskFeatures = filteredFeatures.filter(f => 
  f.properties.risk_class === 'HIGH_RISK'
);

const orderedFeatures = [...lowRiskFeatures, ...mediumRiskFeatures, ...highRiskFeatures];
```

---

##### C. CircleMarker Oluşturma (Line 1089-1115)

```javascript
fireRiskLayer = L.geoJSON(
  { type: 'FeatureCollection', features: orderedFeatures },
  {
    pointToLayer: (feature, latlng) => {
      const riskClass = feature.properties.risk_class || 'SAFE_UNBURNABLE';
      const color = getFireRiskColor(riskClass);
      
      // Boyut: Risk seviyesine göre
      let radius = 3, opacity = 0.5, fillOpacity = 0.4;
      
      if (riskClass === 'HIGH_RISK') {
        radius = 8;
        opacity = 1;
        fillOpacity = 0.85;
      } else if (riskClass === 'MEDIUM_RISK') {
        radius = 6;
        opacity = 0.9;
        fillOpacity = 0.75;
      } else if (riskClass === 'LOW_RISK') {
        radius = 4;
        opacity = 0.7;
        fillOpacity = 0.6;
      }
      
      return L.circleMarker(latlng, {
        radius: radius,
        color: color,
        fillColor: color,
        fillOpacity: fillOpacity,
        weight: 1,
        opacity: opacity
      });
    }
  }
).addTo(map);
```

**Risk Sınıfına Göre Boyut:**
| Sınıf | Radius | Opacity | FillOpacity |
|-------|--------|---------|-------------|
| HIGH_RISK | 8 | 1.0 | 0.85 |
| MEDIUM_RISK | 6 | 0.9 | 0.75 |
| LOW_RISK | 4 | 0.7 | 0.6 |
| Diğer | 3 | 0.5 | 0.4 |

**Görsel Sonuç:**
```
Harita üzerinde renkli daireler
Büyük daireler = Yüksek risk
Küçük daireler = Düşük risk
```

---

##### D. Popup Oluşturma (Line 1117-1124)

```javascript
onEachFeature: (feature, layer) => {
  const props = feature.properties || {};
  const riskClass = props.risk_class || 'SAFE_UNBURNABLE';
  const fireProb = (props.fire_probability * 100).toFixed(1);
  const riskScore = (props.combined_risk_score).toFixed(3);
  
  const popup = `<b>Yangın Risk Analizi</b><br>
    <strong>${getFireRiskLabel(riskClass)}</strong><br>
    Yangın Olasılığı: ${fireProb}%<br>
    Risk Skoru: ${riskScore}<br>
    Konum: (${parseFloat(feature.geometry.coordinates[1]).toFixed(4)}, 
           ${parseFloat(feature.geometry.coordinates[0]).toFixed(4)})`;
  
  layer.bindPopup(popup);
}
```

**Popup Gösterimi:**
```
┌─ Yangın Risk Analizi ─┐
│ Yüksek Risk           │
│ Yangın Olasılığı: 78.2% │
│ Risk Skoru: 0.823     │
│ Konum: (38.2341, 28.3405) │
└───────────────────────┘
```

---

##### E. Legend Oluşturma (Line 1127-1143)

```javascript
fireRiskLegendCtl = L.control({ position: 'bottomright' });
fireRiskLegendCtl.onAdd = function() {
  const div = L.DomUtil.create('div', 'legend');
  div.innerHTML = '<b>Yangın Risk Sınıfları</b><br>' +
    '<div><span style="background:#8b0000; ..."></span>Yüksek Risk (' + highRiskFeatures.length + ')</div>' +
    '<div><span style="background:#e74c3c; ..."></span>Orta Risk (' + mediumRiskFeatures.length + ')</div>' +
    '<div><span style="background:#f39c12; ..."></span>Düşük Risk (' + lowRiskFeatures.filter(f => f.properties.risk_class === 'LOW_RISK').length + ')</div>' +
    '<div><span style="background:#2ecc71; ..."></span>Güvenli (' + lowRiskFeatures.filter(f => f.properties.risk_class !== 'LOW_RISK').length + ')</div>';
  return div;
};
fireRiskLegendCtl.addTo(map);
```

**Legend Gösterimi:**
```
Yangın Risk Sınıfları
● Yüksek Risk (1234)
● Orta Risk (5678)
● Düşük Risk (9012)
● Güvenli (3456)
```

---

#### 5️⃣ YENİ FONKSIYON: `loadHeatmapGrid()` (Line 1175-1286)

**İki ana kısım:**

##### A. Heatmap Verisi Yükleme
```javascript
const response = await fetch('/api/fire-risk/heatmap-data?cell_size=0.05');
if (!response.ok) throw new Error('API hatası: ' + response.status);

const geoJson = await response.json();
if (!geoJson.features || geoJson.features.length === 0) {
  info.textContent = 'Heatmap verisi bulunamadı';
  return;
}
```

##### B. Heatmap Poligon Oluşturma
```javascript
heatmapLayer = L.geoJSON(geoJson, {
  style: (feature) => {
    const riskScore = feature.properties.combined_risk_score || 0;
    
    let color, opacity;
    if (riskScore >= 0.8) {
      color = "#8b0000";
      opacity = 0.85;
    } else if (riskScore >= 0.6) {
      color = "#d70000";
      opacity = 0.80;
    } else if (riskScore >= 0.4) {
      color = "#ff4500";
      opacity = 0.75;
    } else if (riskScore >= 0.2) {
      color = "#ffa500";
      opacity = 0.70;
    } else {
      color = "#ffff00";
      opacity = 0.65;
    }
    
    return {
      color: color,
      weight: 0.5,
      fillColor: color,
      fillOpacity: opacity,
      opacity: 0.8
    };
  }
}).addTo(map);
```

**Renk Şeması:**
```
0.8-1.0: #8b0000 (Koyu Kırmızı) ← En Yüksek Risk
0.6-0.8: #d70000 (Kırmızı)
0.4-0.6: #ff4500 (Turuncu-Kırmızı)
0.2-0.4: #ffa500 (Turuncu)
0.0-0.2: #ffff00 (Sarı) ← En Düşük Risk
```

---

#### 6️⃣ YENİ FONKSIYON: `toggleFireRisk()` (Line 1297-1312)

```javascript
async function toggleFireRisk() {
  // Eğer layer aktif ise, kaldır
  if (fireRiskLayer) {
    map.removeLayer(fireRiskLayer);
    fireRiskLayer = null;
    if (fireRiskLegendCtl) {
      try { fireRiskLegendCtl.remove(); } catch(e) {}
    }
    fireRiskLegendCtl = null;
    updateInfo('ML Yangın Risk Noktaları kapatıldı');
    return;
  }
  
  // Değilse, yükle
  await loadFireRiskPoints();
}
```

**Mantığı:**
- İlk tıkla: Layer açılır
- İkinci tıkla: Layer kapanır
- Temiz kapatış (Legend'i de kaldır)

---

#### 7️⃣ HTML Button (Line 118)

```html
<button id="btnFireRisk" class="btn btn-outline">Riskli Bölgeler</button>
```

---

#### 8️⃣ Event Listener (Line 1491)

```javascript
document.getElementById('btnFireRisk').addEventListener('click', toggleFireRisk);
```

**Akış:**
```
Kullanıcı "Riskli Bölgeler" Butonu'na Tıklar
              ↓
         toggleFireRisk() Çağrılır
              ↓
         loadFireRiskPoints() Çağrılır
              ↓
         API'ye İstek Gönderilir
              ↓
         GeoJSON Alınır
              ↓
         CircleMarker'lar Oluşturulur
              ↓
         Harita Üzerinde Gösterilir
```

---

## 📊 Veri Akışı

### 1. İstek Adımları

```
Frontend                          Backend                      Data
─────────────────────────────────────────────────────────────────────

User Tıkla (btnFireRisk)
         │
         ├─→ toggleFireRisk()
         │   ├─→ loadFireRiskPoints()
         │       └─→ fetch('/api/fire-risk/points?limit=50000')
         │                                    │
         │                                    ├─→ get_fire_risk_points()
         │                                    │   ├─→ load_risk_data()
         │                                    │   │   └─→ pd.read_csv(RISK_DATA_PATH)
         │                                    │   │       └─→ izmir_future_fire_risk_dataset.csv
         │                                    │   │
         │                                    │   ├─→ Filtre (risk_class varsa)
         │                                    │   │
         │                                    │   ├─→ Limit Uygula
         │                                    │   │
         │                                    │   └─→ GeoJSON Oluştur
         │
         ├─ GeoJSON Response Alındı
         │
         ├─→ Validasyonlar
         │   ├─ HTTP Status Kontrolü
         │   ├─ JSON Parse
         │   ├─ Features Varlığı
         │   └─ Koordinat ve İzmir Filtresi
         │
         ├─→ Feature Sıralama
         │
         ├─→ CircleMarker Oluşturma
         │
         ├─→ Popup Ekleme
         │
         ├─→ Legend Ekleme
         │
         └─→ Harita Gösterimi
```

### 2. Veri Şeması

```
CSV Dosyası (Input)
├─ latitude: float (37.5-39.2)
├─ longitude: float (26.0-28.5)
├─ predicted_risk_class: string (SAFE_UNBURNABLE, LOW_RISK, MEDIUM_RISK, HIGH_RISK)
├─ fire_probability: float (0.0-1.0)
├─ high_fire_probability: float (0.0-1.0)
└─ combined_risk_score: float (0.0-1.0)
                    ↓
            API Processing
                    ↓
GeoJSON Feature Collection (Output)
├─ features[]
│  ├─ geometry
│  │  ├─ type: "Point"
│  │  └─ coordinates: [lon, lat]
│  └─ properties
│     ├─ risk_class: string
│     ├─ fire_probability: float
│     ├─ high_fire_probability: float
│     ├─ combined_risk_score: float
│     └─ color: hex string
└─ total: number
```

---

## 🔌 API Endpoints

### Endpoint 1: GET /api/fire-risk/points

| Özellik | Değer |
|---------|-------|
| **URL** | `/api/fire-risk/points` |
| **Method** | GET |
| **Params** | `risk_class` (opt), `limit` (default: 50000) |
| **Response** | GeoJSON FeatureCollection |
| **Use Case** | Risk noktalarını haritada göster |

**Örnek İstek:**
```
GET /api/fire-risk/points?risk_class=HIGH_RISK&limit=1000
```

**Örnek Yanıt:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [28.34, 38.21]},
      "properties": {
        "risk_class": "HIGH_RISK",
        "fire_probability": 0.82,
        "combined_risk_score": 0.89,
        "color": "#8b0000"
      }
    }
  ],
  "total": 1000
}
```

---

### Endpoint 2: GET /api/fire-risk/statistics

| Özellik | Değer |
|---------|-------|
| **URL** | `/api/fire-risk/statistics` |
| **Method** | GET |
| **Params** | Yok |
| **Response** | JSON İstatistikleri |
| **Use Case** | Dashboard'da özet bilgi |

**Örnek Yanıt:**
```json
{
  "total_points": 125000,
  "risk_distribution": {
    "HIGH_RISK": 12345,
    "MEDIUM_RISK": 25678,
    "LOW_RISK": 45678,
    "SAFE_UNBURNABLE": 41299
  },
  "average_fire_probability": 0.456,
  "average_combined_risk_score": 0.523,
  "high_risk_count": 12345,
  "medium_risk_count": 25678,
  "low_risk_count": 45678,
  "safe_count": 41299
}
```

---

### Endpoint 3: GET /api/fire-risk/heatmap-data

| Özellik | Değer |
|---------|-------|
| **URL** | `/api/fire-risk/heatmap-data` |
| **Method** | GET |
| **Params** | `cell_size` (default: 0.05°) |
| **Response** | GeoJSON Polygon FeatureCollection |
| **Use Case** | Heatmap grid gösterimi |

**Örnek İstek:**
```
GET /api/fire-risk/heatmap-data?cell_size=0.05
```

**Örnek Yanıt:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[28.2, 38.2], [28.25, 38.2], [28.25, 38.25], [28.2, 38.25], [28.2, 38.2]]]
      },
      "properties": {
        "combined_risk_score": 0.78,
        "fire_probability": 0.65,
        "risk_class": "HIGH_RISK",
        "color": "#8b0000"
      }
    }
  ],
  "total_cells": 234,
  "cell_size": 0.05
}
```

---

## 🎨 Görselleştirme Detayları

### 1. Risk Noktaları (CircleMarker)

**Özellikleri:**
- Form: Daire
- Boyut: Risk seviyesine göre (3-8 pixel)
- Renk: Risk sınıfına göre
- İnteraktif: Tıklanabilir popup

**Risk Seviyesine Göre Görselik:**
```
HIGH_RISK (Koyu Kırmızı #8b0000)
████ Radius: 8px
████ Opacity: 1.0 (Tamamen Opak)
████ FillOpacity: 0.85

MEDIUM_RISK (Kırmızı #e74c3c)
███ Radius: 6px
███ Opacity: 0.9
███ FillOpacity: 0.75

LOW_RISK (Turuncu #f39c12)
██ Radius: 4px
██ Opacity: 0.7
██ FillOpacity: 0.6

SAFE_UNBURNABLE (Yeşil #2ecc71)
█ Radius: 3px
█ Opacity: 0.5
█ FillOpacity: 0.4
```

---

### 2. Heatmap Grid (Polygon)

**Özellikleri:**
- Form: Kare Poligon (0.05° × 0.05°)
- Boyut: Sabit (hücre boyutu)
- Renk: Risk skoruna göre gradient
- Saydam: Risk skoruna göre opacity

**Risk Skoruna Göre Renk Gradient:**
```
0.8-1.0: #8b0000 (Koyu Kırmızı) - Opacity: 0.85 ← En Yüksek Risk
0.6-0.8: #d70000 (Kırmızı) - Opacity: 0.80
0.4-0.6: #ff4500 (Turuncu-Kırmızı) - Opacity: 0.75
0.2-0.4: #ffa500 (Turuncu) - Opacity: 0.70
0.0-0.2: #ffff00 (Sarı) - Opacity: 0.65 ← En Düşük Risk
```

---

### 3. Legend (Gösterge)

**Konumu:** Sağ Alt (bottomright)

**İçeriği:**
```
┌─────────────────────────────────┐
│ Yangın Risk Sınıfları           │
├─────────────────────────────────┤
│ ● Yüksek Risk (1234)            │
│ ● Orta Risk (5678)              │
│ ● Düşük Risk (9012)             │
│ ● Güvenli (3456)                │
└─────────────────────────────────┘
```

**Sayılar:** Gerçek veri (dinamik)

---

### 4. Popup (İnformasyon Kutusu)

**Tetikleyici:** CircleMarker'a tıkla

**İçeriği:**
```
┌────────────────────────────┐
│ Yangın Risk Analizi        │
├────────────────────────────┤
│ Yüksek Risk                │
│ Yangın Olasılığı: 78.2%   │
│ Risk Skoru: 0.823         │
│ Konum: (38.2341, 28.3405) │
└────────────────────────────┘
```

---

## ✅ Validasyon Mekanizmaları

### 1. Backend Validasyonları

#### A. Dosya Varlığı Kontrolü
```python
if RISK_DATA_PATH.exists():
    return pd.read_csv(RISK_DATA_PATH)
return None
```

#### B. Risk Sınıfı Filtresi
```python
if risk_class:
    df = df[df["predicted_risk_class"] == risk_class]
```

#### C. Limit Uygulaması
```python
df = df.head(limit)
```

#### D. Veri Tipi Kontrolü
```python
"fire_probability": round(row["fire_probability"], 4)
```

---

### 2. Frontend Validasyonları

#### A. HTTP Status Kontrolü
```javascript
if (!response.ok) throw new Error('API hatası: ' + response.status);
```
✓ 200 OK, ✗ 404 Not Found, ✗ 500 Internal Server Error

#### B. JSON Parse Validasyonu
```javascript
const geoJson = await response.json();
```
JSON formatı yanlışsa hata

#### C. Features Varlığı
```javascript
if (!geoJson.features || geoJson.features.length === 0) {
  info.textContent = 'Yangın risk verisi bulunamadı';
  return;
}
```

#### D. Koordinat Varlığı
```javascript
const coords = f.geometry?.coordinates;
if (!coords || coords.length < 2) return false;
```

#### E. Sayısal Veri Kontrolü
```javascript
if (typeof lat !== 'number' || typeof lon !== 'number') {
  console.warn('Sayısal olmayan koordinat');
  return false;
}
```

#### F. İzmir Sınırları Kontrolü
```javascript
function isInIzmir(lat, lon) {
  return lat >= 37.5 && lat <= 39.2 && lon >= 26.0 && lon <= 28.5;
}
```

#### G. Veri Formatlama
```javascript
const fireProb = (props.fire_probability * 100).toFixed(1);
const riskScore = (props.combined_risk_score).toFixed(3);
```
- fire_probability: Yüzdeye çevir
- combined_risk_score: 3 ondalık

#### H. Error Handling
```javascript
try {
  // ... tüm kod
} catch (e) {
  info.textContent = 'Yangın risk yükleme hatası: ' + e.message;
  console.error('Yangın risk yükleme hatası:', e);
}
```

---

## 📈 İş Mantığı Özeti

```
1. CSV Veri
   │
   ├─→ Pandas DataFrame'e Yükleme
   │
   ├─→ Backend İşleme
   │  ├─ Risk Sınıfı Filtresi (opsiyonel)
   │  ├─ Limit Uygulaması
   │  └─ GeoJSON Dönüşümü
   │
   ├─→ API Response
   │  └─ FeatureCollection + Metadata
   │
   ├─→ Frontend'e Gönderme
   │
   ├─→ Frontend Validasyonları
   │  ├─ HTTP Status
   │  ├─ JSON Format
   │  ├─ Koordinat
   │  └─ İzmir Sınırları
   │
   ├─→ Feature Sıralama
   │  └─ Yüksek riskler önde
   │
   ├─→ Görselleştirme
   │  ├─ CircleMarker Oluşturma
   │  ├─ Popup Ekleme
   │  └─ Legend Ekleme
   │
   └─→ Harita Gösterimi
```

---

## 🎯 Özet Tablo

| Bileşen | Dosya | Tür | Satır | Fonksyon |
|---------|-------|-----|-------|----------|
| **Backend** | fire_risk.py | Yeni | 172 | 3 endpoint + 1 utility |
| | main.py | Modifiye | 10, 34 | Import + include_router |
| **Frontend** | index.html | Modifiye | 1029-1491 | 5 fonksiyon + 1 button + 1 listener |
| **Veri** | izmir_future_fire_risk_dataset.csv | Var | - | 125K+ kayıt |

---

## 🚀 Deployment ve Test

### Test Adımları

1. **Backend Test**
   ```bash
   curl http://localhost:8000/api/fire-risk/points?limit=100
   curl http://localhost:8000/api/fire-risk/statistics
   curl http://localhost:8000/api/fire-risk/heatmap-data?cell_size=0.05
   ```

2. **Frontend Test**
   - "Riskli Bölgeler" Butonu'na Tıkla
   - Harita Yüklenme İşlemi (Sarı bar)
   - CircleMarker'lar Görünüyor
   - Legend Sağ Alt'ta Görünüyor
   - CircleMarker'a Tıkla → Popup Açılsın

3. **Heatmap Test**
   - "Heatmap Grid" Butonu'na Tıkla (varsa)
   - Renkli Poligonlar Görünüyor
   - Renk Gradyenti Doğru (Sarı → Kırmızı)

---

## 📝 Sonuç

**Yapılan İş:**
- ✅ ML risk tahminlerini API üzerinden sundum
- ✅ GIS sistemiyle entegrasyon sağladım
- ✅ İnteraktif harita görselleştirmesi oluşturdum
- ✅ Kapsamlı validasyon mekanizmaları
- ✅ Heatmap grid analizi

**Teknoloji Stack:**
- Backend: FastAPI + Pandas
- Frontend: Leaflet.js + JavaScript
- Veri: CSV (Pandas DataFrame)
- Format: GeoJSON

**Beklenen Sonuç:**
- Kullanıcı "Riskli Bölgeler" butonuna tıklar
- 50K risk noktası haritada gösterilir
- Renk ve boyut ile risk seviyesi belirtilir
- Tıklandığında detaylar popup'ta görünür
- Legend sayılarla kategori gösterilir
