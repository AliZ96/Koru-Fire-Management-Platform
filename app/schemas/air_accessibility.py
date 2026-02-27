"""
Hava Erişilebilirlik API için Pydantic şemaları
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class AirAccessibilityLevel(str, Enum):
    """Hava erişilebilirlik seviyeleri"""
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    MODERATE = "MODERATE"
    DIFFICULT = "DIFFICULT"
    RESTRICTED = "RESTRICTED"


class AircraftType(str, Enum):
    """Hava aracı tipleri"""
    HELICOPTER = "HELICOPTER"
    FIXED_WING = "FIXED_WING"
    DRONE = "DRONE"


class TerrainType(str, Enum):
    """Arazi tipleri"""
    FLAT = "FLAT"
    HILLY = "HILLY"
    MOUNTAINOUS = "MOUNTAINOUS"
    FOREST = "FOREST"
    WATER = "WATER"


class AirAccessibilityRequest(BaseModel):
    """Hava erişilebilirlik değerlendirme isteği"""
    latitude: float = Field(..., ge=-90, le=90, description="Enlem (-90 ile 90 arası)")
    longitude: float = Field(..., ge=-180, le=180, description="Boylam (-180 ile 180 arası)")
    elevation: float = Field(default=0, ge=0, description="Rakım (metre)")
    terrain_type: TerrainType = Field(default=TerrainType.FLAT, description="Arazi tipi")
    vegetation_density: float = Field(default=0.5, ge=0, le=1, description="Bitki örtüsü yoğunluğu (0-1)")
    aircraft_type: AircraftType = Field(default=AircraftType.HELICOPTER, description="Hava aracı tipi")
    
    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 38.4192,
                "longitude": 27.1287,
                "elevation": 150,
                "terrain_type": "HILLY",
                "vegetation_density": 0.6,
                "aircraft_type": "HELICOPTER"
            }
        }


class AirAccessibilityResponse(BaseModel):
    """Hava erişilebilirlik değerlendirme sonucu"""
    accessibility_level: AirAccessibilityLevel = Field(..., description="Erişilebilirlik seviyesi")
    score: float = Field(..., ge=0, le=100, description="Erişilebilirlik skoru (0-100)")
    distance_to_base_km: float = Field(..., description="En yakın hava üssüne mesafe (km)")
    nearest_base: str = Field(..., description="En yakın hava üssü adı")
    eta_minutes: Optional[float] = Field(None, description="Tahmini varış süresi (dakika)")
    aircraft_type: str = Field(..., description="Hava aracı tipi")
    terrain_type: str = Field(..., description="Arazi tipi")
    elevation_m: float = Field(..., description="Rakım (metre)")
    vegetation_density: float = Field(..., description="Bitki örtüsü yoğunluğu")
    reasons: List[str] = Field(default=[], description="Değerlendirme nedenleri")
    recommendations: List[str] = Field(default=[], description="Öneriler")
    nearest_water_source: Optional[str] = Field(None, description="En yakın su kaynağı (acil iniş)")
    water_distance_km: Optional[float] = Field(None, description="Su kaynağına mesafe (km)")
    
    class Config:
        json_schema_extra = {
            "example": {
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
        }


class LocationInput(BaseModel):
    """Konum girişi"""
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    elevation: float = Field(default=0, ge=0)
    terrain_type: str = Field(default="FLAT")
    vegetation_density: float = Field(default=0.5, ge=0, le=1)


class BatchAccessibilityRequest(BaseModel):
    """Toplu erişilebilirlik değerlendirme isteği"""
    locations: List[LocationInput] = Field(..., min_length=1, max_length=1000, description="Konum listesi")
    aircraft_type: AircraftType = Field(default=AircraftType.HELICOPTER, description="Hava aracı tipi")
    
    class Config:
        json_schema_extra = {
            "example": {
                "locations": [
                    {"lat": 38.4192, "lon": 27.1287, "elevation": 150, "terrain_type": "HILLY"},
                    {"lat": 38.3500, "lon": 27.0500, "elevation": 200, "terrain_type": "FOREST"}
                ],
                "aircraft_type": "HELICOPTER"
            }
        }


class GridMapRequest(BaseModel):
    """Grid harita isteği"""
    min_lon: float = Field(..., ge=-180, le=180, description="Minimum boylam")
    min_lat: float = Field(..., ge=-90, le=90, description="Minimum enlem")
    max_lon: float = Field(..., ge=-180, le=180, description="Maksimum boylam")
    max_lat: float = Field(..., ge=-90, le=90, description="Maksimum enlem")
    grid_size: float = Field(default=0.01, gt=0, le=1, description="Grid hücre boyutu (derece)")
    aircraft_type: AircraftType = Field(default=AircraftType.HELICOPTER, description="Hava aracı tipi")
    
    class Config:
        json_schema_extra = {
            "example": {
                "min_lon": 26.8,
                "min_lat": 38.2,
                "max_lon": 27.3,
                "max_lat": 38.6,
                "grid_size": 0.02,
                "aircraft_type": "HELICOPTER"
            }
        }


class AirBaseInfo(BaseModel):
    """Hava üssü bilgisi"""
    name: str
    latitude: float
    longitude: float
    type: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Adnan Menderes Havalimanı",
                "latitude": 38.2924,
                "longitude": 27.1570,
                "type": "airport"
            }
        }


class AirBasesResponse(BaseModel):
    """Hava üsleri listesi yanıtı"""
    air_bases: List[AirBaseInfo]
    total_count: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "air_bases": [
                    {
                        "name": "Adnan Menderes Havalimanı",
                        "latitude": 38.2924,
                        "longitude": 27.1570,
                        "type": "airport"
                    }
                ],
                "total_count": 3
            }
        }
