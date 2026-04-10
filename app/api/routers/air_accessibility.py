"""
Hava Erişilebilirliği API Router (LLF-2.3)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Any, Dict

from app.schemas.air_accessibility import (
    AirAccessibilityRequest,
    AirAccessibilityResponse,
    BatchAccessibilityRequest,
    GridMapRequest,
    AirBaseInfo,
    AirBasesResponse,
    AircraftType,
    TerrainType
)
from app.services.air_accessibility_service import (
    AirAccessibilityService,
    AirAccessibilityLevel,
    AircraftType as ServiceAircraftType,
    TerrainType as ServiceTerrainType
)

router = APIRouter(prefix="/api/air-accessibility", tags=["air-accessibility"])
MAX_GRID_POINTS = 8000
MIN_GRID_SIZE = 0.005

# Servis instance
air_service = AirAccessibilityService()


@router.post("/classify", response_model=AirAccessibilityResponse)
async def classify_air_accessibility(request: AirAccessibilityRequest):
    """
    Tek bir yangın risk noktası için hava erişilebilirliğini değerlendirir
    
    **LLF-2.3**: Kara erişimi bulunmayan yangın risk bölgelerinin hava araçları
    açısından erişilebilirliğinin değerlendirilmesi.
    
    ## Parametreler:
    - **latitude**: Enlem koordinatı (-90 ile 90 arası)
    - **longitude**: Boylam koordinatı (-180 ile 180 arası)
    - **elevation**: Rakım (metre cinsinden, varsayılan: 0)
    - **terrain_type**: Arazi tipi (FLAT, HILLY, MOUNTAINOUS, FOREST, WATER)
    - **vegetation_density**: Bitki örtüsü yoğunluğu (0-1 arası, varsayılan: 0.5)
    - **aircraft_type**: Hava aracı tipi (HELICOPTER, FIXED_WING, DRONE)
    
    ## Erişilebilirlik Seviyeleri:
    - **EXCELLENT**: Her türlü hava aracı kolayca erişebilir
    - **GOOD**: Hava araçları güvenli şekilde erişebilir
    - **MODERATE**: Belirli kısıtlamalarla erişilebilir
    - **DIFFICULT**: Sadece deneyimli pilotlar erişebilir
    - **RESTRICTED**: Çok sınırlı veya hiç erişim yok
    
    ## Dönüş Değerleri:
    - Erişilebilirlik seviyesi ve skoru (0-100)
    - En yakın hava üssü ve mesafe
    - Tahmini varış süresi
    - Engeller ve öneriler
    """
    try:
        result = air_service.classify_air_accessibility(
            latitude=request.latitude,
            longitude=request.longitude,
            elevation=request.elevation,
            terrain_type=ServiceTerrainType(request.terrain_type.value),
            vegetation_density=request.vegetation_density,
            aircraft_type=ServiceAircraftType(request.aircraft_type.value)
        )
        
        return AirAccessibilityResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erişilebilirlik değerlendirmesi başarısız: {str(e)}")


@router.post("/batch-classify")
async def batch_classify_air_accessibility(request: BatchAccessibilityRequest):
    """
    Birden fazla lokasyon için toplu hava erişilebilirlik değerlendirmesi
    
    ## Kullanım Alanları:
    - Yangın risk haritası üzerindeki tüm yüksek risk noktalarının değerlendirilmesi
    - Müdahale önceliklerinin belirlenmesi
    - Alternatif erişim rotalarının planlanması
    
    ## Limitler:
    - Maksimum 1000 nokta tek istekte işlenebilir
    - Daha fazla nokta için istekleri bölün
    """
    try:
        locations = [loc.model_dump() for loc in request.locations]
        results = air_service.batch_classify(
            locations=locations,
            aircraft_type=ServiceAircraftType(request.aircraft_type.value)
        )
        
        return {
            "results": results,
            "total_count": len(results),
            "aircraft_type": request.aircraft_type.value
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Toplu değerlendirme başarısız: {str(e)}")


@router.post("/grid-map")
async def get_accessibility_grid_map(request: GridMapRequest):
    """
    Bir bölge için grid tabanlı hava erişilebilirlik haritası oluşturur
    
    ## GeoJSON Çıktısı:
    Grid üzerindeki her nokta için erişilebilirlik değerlendirmesi içeren
    GeoJSON FeatureCollection döndürür. Harita görselleştirmesi için uygundur.
    
    ## Performans Notları:
    - Grid boyutu küçüldükçe işlem süresi artar
    - Önerilen grid_size: 0.01 - 0.05 (yaklaşık 1-5 km)
    - Büyük alanlar için grid_size'ı artırın
    
    ## Kullanım Örneği:
    İzmir bölgesi için tüm alanın helikopter erişilebilirlik haritası:
    ```
    {
      "min_lon": 26.8, "min_lat": 38.2,
      "max_lon": 27.3, "max_lat": 38.6,
      "grid_size": 0.02,
      "aircraft_type": "HELICOPTER"
    }
    ```
    """
    try:
        # Bounding box tuple oluştur
        bbox = (request.min_lon, request.min_lat, request.max_lon, request.max_lat)
        if request.grid_size < MIN_GRID_SIZE:
            raise HTTPException(
                status_code=422,
                detail=f"grid_size must be >= {MIN_GRID_SIZE}",
            )
        if request.min_lon >= request.max_lon or request.min_lat >= request.max_lat:
            raise HTTPException(status_code=422, detail="Invalid bbox bounds")
        lon_steps = int((request.max_lon - request.min_lon) / request.grid_size) + 1
        lat_steps = int((request.max_lat - request.min_lat) / request.grid_size) + 1
        estimated_points = lon_steps * lat_steps
        if estimated_points > MAX_GRID_POINTS:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Requested grid too dense ({estimated_points} points). "
                    f"Max allowed: {MAX_GRID_POINTS}. Increase grid_size or reduce bbox."
                ),
            )
        
        # Grid haritası oluştur
        result = air_service.get_accessibility_map(
            bbox=bbox,
            grid_size=request.grid_size,
            aircraft_type=ServiceAircraftType(request.aircraft_type.value)
        )
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grid haritası oluşturulamadı: {str(e)}")


@router.get("/air-bases", response_model=AirBasesResponse)
async def get_air_bases():
    """
    İzmir bölgesindeki hava üslerinin listesini döndürür
    
    ## İçerik:
    - Havaalanları
    - Askeri hava üsleri
    - Heliportlar
    
    ## Kullanım:
    Hava araçlarının kalkış noktalarını görmek ve mesafe hesaplamalarını
    anlamak için kullanılır.
    """
    air_bases = [
        AirBaseInfo(
            name=base['name'],
            latitude=base['lat'],
            longitude=base['lon'],
            type=base['type']
        )
        for base in AirAccessibilityService.AIR_BASES
    ]
    
    return AirBasesResponse(
        air_bases=air_bases,
        total_count=len(air_bases)
    )


@router.get("/accessibility-levels")
async def get_accessibility_levels():
    """
    Tüm erişilebilirlik seviyelerini ve açıklamalarını döndürür
    
    Sistem tarafından kullanılan erişilebilirlik sınıflandırma seviyelerini
    ve her seviyenin anlamını açıklar.
    """
    return {
        "levels": [
            {
                "level": "EXCELLENT",
                "score_range": "85-100",
                "description": "Her türlü hava aracı kolayca erişebilir",
                "color": "#2ecc71",
                "icon": "✅"
            },
            {
                "level": "GOOD",
                "score_range": "70-84",
                "description": "Hava araçları güvenli şekilde erişebilir",
                "color": "#3498db",
                "icon": "👍"
            },
            {
                "level": "MODERATE",
                "score_range": "50-69",
                "description": "Belirli kısıtlamalarla erişilebilir",
                "color": "#f39c12",
                "icon": "⚠️"
            },
            {
                "level": "DIFFICULT",
                "score_range": "30-49",
                "description": "Sadece deneyimli pilotlar erişebilir",
                "color": "#e74c3c",
                "icon": "⛔"
            },
            {
                "level": "RESTRICTED",
                "score_range": "0-29",
                "description": "Çok sınırlı veya hiç erişim yok",
                "color": "#8b0000",
                "icon": "🚫"
            }
        ],
        "factors": [
            {
                "factor": "distance_to_base",
                "weight": "0-40 points",
                "description": "Hava üssüne olan mesafe"
            },
            {
                "factor": "elevation",
                "weight": "0-20 points",
                "description": "Yüksek rakım (>1500m) zorluk yaratır"
            },
            {
                "factor": "terrain",
                "weight": "0-15 points",
                "description": "Dağlık ve ormanlık araziler daha zor"
            },
            {
                "factor": "vegetation",
                "weight": "0-15 points",
                "description": "Yoğun bitki örtüsü iniş zorlaştırır"
            },
            {
                "factor": "water_proximity",
                "weight": "+5 points",
                "description": "Yakın su kaynağı acil iniş avantajı"
            }
        ]
    }


@router.get("/aircraft-types")
async def get_aircraft_types():
    """
    Desteklenen hava aracı tiplerini ve özelliklerini döndürür
    """
    return {
        "aircraft_types": [
            {
                "type": "HELICOPTER",
                "name": "Helikopter",
                "max_range_km": AirAccessibilityService.HELICOPTER_RANGE_KM,
                "avg_speed_kmh": AirAccessibilityService.HELICOPTER_SPEED_KMH,
                "advantages": [
                    "Dikey iniş-kalkış",
                    "Dar alanlara erişim",
                    "Hassas manevra kabiliyeti"
                ],
                "limitations": [
                    "Kısıtlı menzil",
                    "Hava koşullarına duyarlı",
                    "Yüksek işletme maliyeti"
                ]
            },
            {
                "type": "FIXED_WING",
                "name": "Sabit Kanatlı Uçak",
                "max_range_km": AirAccessibilityService.FIXED_WING_RANGE_KM,
                "avg_speed_kmh": AirAccessibilityService.FIXED_WING_SPEED_KMH,
                "advantages": [
                    "Uzun menzil",
                    "Yüksek hız",
                    "Geniş kapsam alanı"
                ],
                "limitations": [
                    "İniş pisti gerekir",
                    "Dağlık arazilerde sınırlı",
                    "Su atımı için geniş alan gerekir"
                ]
            },
            {
                "type": "DRONE",
                "name": "İHA/Drone",
                "max_range_km": AirAccessibilityService.DRONE_RANGE_KM,
                "avg_speed_kmh": AirAccessibilityService.DRONE_SPEED_KMH,
                "advantages": [
                    "Keşif ve gözlem",
                    "Düşük maliyet",
                    "İnsansız operasyon"
                ],
                "limitations": [
                    "Kısa menzil",
                    "Düşük yük kapasitesi",
                    "Rüzgara duyarlı"
                ]
            }
        ]
    }


@router.get("/terrain-types")
async def get_terrain_types():
    """
    Desteklenen arazi tiplerini ve zorluklarını döndürür
    """
    return {
        "terrain_types": [
            {
                "type": "FLAT",
                "name": "Düz Arazi",
                "difficulty": "Kolay",
                "penalty": 0,
                "description": "İdeal iniş koşulları"
            },
            {
                "type": "HILLY",
                "name": "Tepeli Arazi",
                "difficulty": "Orta",
                "penalty": 5,
                "description": "Manevra kabiliyeti gerektirir"
            },
            {
                "type": "MOUNTAINOUS",
                "name": "Dağlık Arazi",
                "difficulty": "Zor",
                "penalty": 15,
                "description": "Yüksek rakım ve hava akımları"
            },
            {
                "type": "FOREST",
                "name": "Ormanlık Alan",
                "difficulty": "Zor",
                "penalty": 10,
                "description": "İniş alanı sınırlı, ağaç engelleri"
            },
            {
                "type": "WATER",
                "name": "Su Üzeri",
                "difficulty": "Kolay",
                "penalty": -5,
                "description": "Helikopter için avantajlı (amfibi olmayan uçaklar için uygunsuz)"
            }
        ]
    }


@router.get("/quick-assess")
async def quick_assessment(
    lat: float = Query(..., ge=-90, le=90, description="Enlem"),
    lon: float = Query(..., ge=-180, le=180, description="Boylam"),
    aircraft: AircraftType = Query(AircraftType.HELICOPTER, description="Hava aracı tipi")
):
    """
    Hızlı erişilebilirlik değerlendirmesi (minimal parametreler)
    
    Sadece konum ve hava aracı tipi ile basitleştirilmiş değerlendirme.
    Arazi ve bitki örtüsü varsayılan değerlerle hesaplanır.
    """
    try:
        result = air_service.classify_air_accessibility(
            latitude=lat,
            longitude=lon,
            elevation=0,
            terrain_type=ServiceTerrainType.FLAT,
            vegetation_density=0.5,
            aircraft_type=ServiceAircraftType(aircraft.value)
        )
        
        # Sadece önemli bilgileri döndür
        return {
            "accessibility_level": result['accessibility_level'],
            "score": result['score'],
            "distance_km": result['distance_to_base_km'],
            "eta_minutes": result['eta_minutes'],
            "nearest_base": result['nearest_base'],
            "summary": f"{result['accessibility_level']} erişilebilirlik: "
                      f"{result['distance_to_base_km']:.1f}km uzaklıkta, "
                      f"~{result['eta_minutes']:.0f} dakika"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hızlı değerlendirme başarısız: {str(e)}")
