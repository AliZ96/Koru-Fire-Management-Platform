"""
Kara Erişilebilirlik & Entegre Risk-Erişilebilirlik API Router
Sprint 6 / LLF-2.2

Endpoint grupları
-----------------
/api/accessibility/ground/*
    Kara erişilebilirlik haritası, nokta listesi, özet istatistik, nokta sınıflandırma

/api/accessibility/integrated/*
    Yangın riski + kara erişilebilirlik entegre haritası, özet, kritik bölgeler

/api/accessibility/levels
    Sınıf tanımları ve öncelik matrisi (referans endpoint)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.ground_accessibility_service import GroundAccessibilityService

router = APIRouter(
    prefix="/api/accessibility",
    tags=["accessibility"],
)

# Uygulama genelinde tek instance (veri önbellekleme için)
_svc = GroundAccessibilityService()


# ===========================================================================
# Kara Erişilebilirlik
# ===========================================================================

@router.get(
    "/ground/map",
    summary="Kara Erişilebilirlik Haritası (GeoJSON)",
    response_description="GeoJSON FeatureCollection – kara erişilebilirlik grid poligonları",
)
async def get_ground_map(
    access_class: Optional[str] = Query(
        None,
        description="Filtre: HIGH | MEDIUM | LOW | NO_ACCESS",
    ),
    min_lon: Optional[float] = Query(None, description="Bounding-box minimum boylam"),
    min_lat: Optional[float] = Query(None, description="Bounding-box minimum enlem"),
    max_lon: Optional[float] = Query(None, description="Bounding-box maksimum boylam"),
    max_lat: Optional[float] = Query(None, description="Bounding-box maksimum enlem"),
    cell_size: float = Query(0.03, gt=0, le=1, description="Poligon hücre boyutu (derece)"),
):
    """
    Kara erişilebilirlik grid haritasını **GeoJSON FeatureCollection** olarak döndürür.

    Her poligon şu `properties` alanlarını içerir:

    | Alan | Açıklama |
    |------|----------|
    | `ground_access_class` | HIGH / MEDIUM / LOW / NO_ACCESS |
    | `ground_access_score` | 3 / 2 / 1 / 0 |
    | `dist_to_road_m` | En yakın yola mesafe (metre) |
    | `slope_deg` | Ortalama eğim (derece) |
    | `color` | Harita görselleştirme renk kodu |

    ## Sınıf Kriterleri
    | Sınıf | Skor | Yol Mesafesi | Eğim |
    |-------|------|--------------|------|
    | HIGH | 3 | ≤ 200 m | ≤ 15° |
    | MEDIUM | 2 | ≤ 500 m | ≤ 25° |
    | LOW | 1 | > 500 m | ≤ 40° |
    | NO_ACCESS | 0 | — | > 40° veya yanmaz arazi |
    """
    try:
        bbox = None
        if all(v is not None for v in [min_lon, min_lat, max_lon, max_lat]):
            bbox = (min_lon, min_lat, max_lon, max_lat)
        return _svc.get_ground_map(
            access_class=access_class,
            bbox=bbox,
            cell_size=cell_size,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/ground/points",
    summary="Kara Erişilebilirlik Nokta Listesi",
    response_description="Filtrelenebilir kara erişilebilirlik nokta dizisi",
)
async def get_ground_points(
    access_class: Optional[str] = Query(
        None,
        description="Filtre: HIGH | MEDIUM | LOW | NO_ACCESS",
    ),
    min_lon: Optional[float] = Query(None),
    min_lat: Optional[float] = Query(None),
    max_lon: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    limit: int = Query(5000, gt=0, le=10000, description="Maksimum kayıt sayısı"),
):
    """
    Kara erişilebilirlik noktalarını **liste formatında** döndürür.

    Haritaya ek olarak tablo veya analiz aracı olarak kullanılabilir.
    Her nesne: `center_lat`, `center_lon`, `ground_access_class`,
    `ground_access_score`, `dist_to_road_m`, `slope_deg`.
    """
    try:
        bbox = None
        if all(v is not None for v in [min_lon, min_lat, max_lon, max_lat]):
            bbox = (min_lon, min_lat, max_lon, max_lat)
        return _svc.get_ground_points(
            access_class=access_class,
            bbox=bbox,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/ground/summary",
    summary="Kara Erişilebilirlik Özet İstatistikleri",
    response_description="Dağılım, ortalama yol mesafesi, eğim ve erişilemeyen alan yüzdesi",
)
async def get_ground_summary():
    """
    Kara erişilebilirlik **özet istatistiklerini** döndürür.

    Yanıt alanları:
    - `total_cells` – toplam grid hücre sayısı
    - `ground_access_distribution` – sınıf başına hücre sayısı
    - `average_dist_to_road_m` – ortalama yol mesafesi
    - `average_slope_deg` – ortalama eğim
    - `no_access_count` / `no_access_percentage` – erişilemeyen alan istatistikleri
    """
    try:
        return _svc.get_ground_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/ground/classify",
    summary="Tek Nokta Kara Erişilebilirlik Sınıflandırması",
    response_description="En yakın komşu grid hücresine göre kara erişim sınıfı",
)
async def classify_ground_point(
    lat: float = Query(..., ge=-90, le=90, description="Enlem koordinatı"),
    lon: float = Query(..., ge=-180, le=180, description="Boylam koordinatı"),
):
    """
    Verilen koordinat için **en yakın grid hücresinin** kara erişilebilirlik
    sınıfını döndürür (en yakın komşu / nearest-neighbour yöntemi).

    Dönüş alanları:
    - `input` – girdi koordinatları
    - `nearest_cell` – eşleşen hücre merkezi
    - `distance_to_cell_km` – girdi–hücre uzaklığı (km)
    - `ground_access_class` / `ground_access_score`
    - `dist_to_road_m` / `slope_deg`
    """
    try:
        return _svc.classify_point(lat=lat, lon=lon)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ===========================================================================
# Entegre Risk-Erişilebilirlik
# ===========================================================================

@router.get(
    "/integrated/map",
    summary="Entegre Yangın Riski + Kara Erişilebilirlik Haritası (GeoJSON)",
    response_description="GeoJSON FeatureCollection – öncelik seviyeli birleşik harita",
)
async def get_integrated_map(
    min_lon: Optional[float] = Query(None),
    min_lat: Optional[float] = Query(None),
    max_lon: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    cell_size: float = Query(0.03, gt=0, le=1, description="Poligon hücre boyutu (derece)"),
    min_fire_risk: Optional[str] = Query(
        None,
        description="Minimum yangın riski filtresi: LOW_RISK | MEDIUM_RISK | HIGH_RISK",
    ),
    air_required_only: bool = Query(
        False,
        description="True → yalnızca hava müdahalesi gereken alanları getir",
    ),
):
    """
    Yangın risk verisiyle kara erişilebilirliği **entegre ederek** harita döndürür.

    Her hücre için **spatial join** (en yakın komşu) yöntemiyle kara erişim bilgisi
    fire-risk verisiyle eşleştirilir.

    `properties` alanları:

    | Alan | Açıklama |
    |------|----------|
    | `fire_risk_class` | ML tahmin sınıfı |
    | `fire_probability` | ML yangın olasılığı |
    | `combined_risk_score` | Birleşik risk skoru (0-1) |
    | `ground_access_class` | Kara erişim sınıfı |
    | `ground_access_score` | Kara erişim skoru (0-3) |
    | `air_access_required` | Hava müdahalesi gerekli mi |
    | `priority_level` | CRITICAL / HIGH / MEDIUM / LOW |
    | `color` | Öncelik renk kodu |

    ## Öncelik Matrisi
    | Yangın Riski | Kara Erişim | Öncelik | Hava Gerekli |
    |-------------|------------|---------|-------------|
    | HIGH_RISK | NO_ACCESS | **CRITICAL** | ✅ |
    | HIGH_RISK | LOW | HIGH | ✅ |
    | MEDIUM_RISK | NO_ACCESS | HIGH | ✅ |
    | HIGH_RISK | MEDIUM/HIGH | HIGH/MEDIUM | ❌ |
    | MEDIUM_RISK | LOW/MEDIUM | MEDIUM | ✅/❌ |
    | LOW_RISK / SAFE | — | LOW/MEDIUM | ❌ |
    """
    try:
        bbox = None
        if all(v is not None for v in [min_lon, min_lat, max_lon, max_lat]):
            bbox = (min_lon, min_lat, max_lon, max_lat)
        return _svc.get_integrated_map(
            bbox=bbox,
            cell_size=cell_size,
            min_fire_risk=min_fire_risk,
            air_required_only=air_required_only,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/integrated/summary",
    summary="Entegre Risk-Erişilebilirlik Özet İstatistikleri",
    response_description="Kritik bölge, hava müdahalesi ve dağılım istatistikleri",
)
async def get_integrated_summary():
    """
    Yangın riski ve kara erişilebilirliğinin **kombine özet istatistiklerini** döndürür.

    Yanıt alanları:
    - `fire_risk_distribution` – yangın riski sınıfı başına hücre sayısı
    - `ground_access_distribution` – kara erişim sınıfı başına eşleşen hücre sayısı
    - `critical_zones_count` – HIGH_RISK + NO_ACCESS kombinasyon sayısı
    - `air_only_access_count` – hava müdahalesi gereken toplam alan sayısı
    - `joint_high_risk_no_access` – yalnızca en kritik kombinasyon sayısı
    """
    try:
        return _svc.get_integrated_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/integrated/critical-zones",
    summary="Kritik Bölgeler – Sadece Hava Müdahalesi ile Erişilebilir",
    response_description="GeoJSON FeatureCollection – CRITICAL ve HIGH öncelikli hava-gerekli bölgeler",
)
async def get_critical_zones(
    cell_size: float = Query(0.03, gt=0, le=1),
    min_lon: Optional[float] = Query(None),
    min_lat: Optional[float] = Query(None),
    max_lon: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
):
    """
    **Hava müdahalesi gereken kritik bölgeleri** döndürür.

    Filtre: kara erişimi NO_ACCESS veya LOW **ve** yangın riski HIGH_RISK veya MEDIUM_RISK.

    Bu katman;
    - Hava araçlarının öncelikli müdahale planlaması,
    - Görselleştirme araçlarındaki acil müdahale katmanı,
    - Downstream sistem modüllerine kritik bölge beslemesi

    için tasarlanmıştır.
    """
    try:
        bbox = None
        if all(v is not None for v in [min_lon, min_lat, max_lon, max_lat]):
            bbox = (min_lon, min_lat, max_lon, max_lat)
        return _svc.get_integrated_map(
            bbox=bbox,
            cell_size=cell_size,
            air_required_only=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ===========================================================================
# Referans / Meta
# ===========================================================================

@router.get(
    "/levels",
    summary="Erişilebilirlik Sınıf Tanımları ve Öncelik Matrisi",
    response_description="Sınıf kriterleri, skorlar, renkler ve öncelik matrisi",
)
async def get_accessibility_levels():
    """
    Kara erişilebilirlik **sınıf tanımlarını** ve **öncelik matrisini** döndürür.

    Görselleştirme araçları ve downstream modüllerin renk/sınıf eşlemesi için
    sistem genelinde tek kaynak (single source of truth) referans endpoint'idir.
    """
    return {
        "ground_access_classes": [
            {
                "access_class": "HIGH",
                "score": 3,
                "color": "#2ecc71",
                "description": "Yüksek kara erişimi: ≤ 200 m yol mesafesi, ≤ 15° eğim",
                "criteria": {"max_road_dist_m": 200, "max_slope_deg": 15},
            },
            {
                "access_class": "MEDIUM",
                "score": 2,
                "color": "#f39c12",
                "description": "Orta kara erişimi: ≤ 500 m yol mesafesi, ≤ 25° eğim",
                "criteria": {"max_road_dist_m": 500, "max_slope_deg": 25},
            },
            {
                "access_class": "LOW",
                "score": 1,
                "color": "#e74c3c",
                "description": "Düşük kara erişimi: > 500 m yol mesafesi veya 25–40° eğim",
                "criteria": {"max_road_dist_m": None, "max_slope_deg": 40},
            },
            {
                "access_class": "NO_ACCESS",
                "score": 0,
                "color": "#8b0000",
                "description": "Erişilemeyen: yanmaz arazi (burnable=0) veya > 40° eğim",
                "criteria": {
                    "max_road_dist_m": None,
                    "max_slope_deg": None,
                    "note": "burnable=0 OR slope > 40°",
                },
            },
        ],
        "priority_matrix": [
            {"fire_risk": "HIGH_RISK",      "ground_access": "NO_ACCESS", "priority": "CRITICAL", "air_required": True},
            {"fire_risk": "HIGH_RISK",      "ground_access": "LOW",       "priority": "HIGH",     "air_required": True},
            {"fire_risk": "HIGH_RISK",      "ground_access": "MEDIUM",    "priority": "HIGH",     "air_required": False},
            {"fire_risk": "HIGH_RISK",      "ground_access": "HIGH",      "priority": "MEDIUM",   "air_required": False},
            {"fire_risk": "MEDIUM_RISK",    "ground_access": "NO_ACCESS", "priority": "HIGH",     "air_required": True},
            {"fire_risk": "MEDIUM_RISK",    "ground_access": "LOW",       "priority": "MEDIUM",   "air_required": True},
            {"fire_risk": "MEDIUM_RISK",    "ground_access": "MEDIUM",    "priority": "MEDIUM",   "air_required": False},
            {"fire_risk": "MEDIUM_RISK",    "ground_access": "HIGH",      "priority": "LOW",      "air_required": False},
            {"fire_risk": "LOW_RISK",       "ground_access": "NO_ACCESS", "priority": "MEDIUM",   "air_required": False},
            {"fire_risk": "LOW_RISK",       "ground_access": "LOW",       "priority": "LOW",      "air_required": False},
            {"fire_risk": "LOW_RISK",       "ground_access": "MEDIUM",    "priority": "LOW",      "air_required": False},
            {"fire_risk": "LOW_RISK",       "ground_access": "HIGH",      "priority": "LOW",      "air_required": False},
            {"fire_risk": "SAFE_UNBURNABLE","ground_access": "NO_ACCESS", "priority": "LOW",      "air_required": False},
            {"fire_risk": "SAFE_UNBURNABLE","ground_access": "LOW",       "priority": "LOW",      "air_required": False},
            {"fire_risk": "SAFE_UNBURNABLE","ground_access": "MEDIUM",    "priority": "LOW",      "air_required": False},
            {"fire_risk": "SAFE_UNBURNABLE","ground_access": "HIGH",      "priority": "LOW",      "air_required": False},
        ],
    }
