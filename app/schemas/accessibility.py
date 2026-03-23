"""
Kara Erişilebilirlik & Entegre Risk-Erişilebilirlik API Şemaları

Sprint 6 / LLF-2.2 kapsamı:
- Kara erişilebilirlik sınıflandırma şemaları
- Entegre yangın riski + erişilebilirlik yanıt şemaları
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GroundAccessClass(str, Enum):
    HIGH = "HIGH"           # ≤200 m yol, ≤15° eğim
    MEDIUM = "MEDIUM"       # ≤500 m yol, ≤25° eğim
    LOW = "LOW"             # Zor ama mümkün
    NO_ACCESS = "NO_ACCESS" # Yanmaz arazi veya >40° eğim


class FireRiskClass(str, Enum):
    SAFE_UNBURNABLE = "SAFE_UNBURNABLE"
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"


class PriorityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ---------------------------------------------------------------------------
# Ground Accessibility
# ---------------------------------------------------------------------------

class GroundAccessibilityPoint(BaseModel):
    """Tek bir grid hücresinin kara erişilebilirlik bilgisi"""
    center_lat: float = Field(..., description="Grid hücre merkez enlemi")
    center_lon: float = Field(..., description="Grid hücre merkez boylamı")
    ground_access_class: GroundAccessClass = Field(..., description="Kara erişim sınıfı")
    ground_access_score: int = Field(..., ge=0, le=3, description="Kara erişim skoru (0=Erişilemez, 3=Yüksek)")
    dist_to_road_m: Optional[float] = Field(None, description="En yakın yola mesafe (metre)")
    slope_deg: Optional[float] = Field(None, description="Eğim (derece)")
    color: Optional[str] = Field(None, description="Görselleştirme renk kodu")

    model_config = {
        "json_schema_extra": {
            "example": {
                "center_lat": 38.42,
                "center_lon": 27.13,
                "ground_access_class": "MEDIUM",
                "ground_access_score": 2,
                "dist_to_road_m": 320.5,
                "slope_deg": 18.3,
                "color": "#f39c12",
            }
        }
    }


class GroundAccessibilitySummaryResponse(BaseModel):
    """Kara erişilebilirlik özet istatistikleri"""
    total_cells: int = Field(..., description="Toplam grid hücre sayısı")
    ground_access_distribution: Dict[str, int] = Field(
        ..., description="Erişilebilirlik sınıfı başına hücre sayısı"
    )
    average_dist_to_road_m: Optional[float] = Field(None, description="Ortalama yol mesafesi (m)")
    average_slope_deg: Optional[float] = Field(None, description="Ortalama eğim (derece)")
    no_access_count: int = Field(..., description="Erişilemeyen hücre sayısı")
    no_access_percentage: float = Field(..., description="Erişilemeyen hücre yüzdesi")


class ClassifyGroundPointResponse(BaseModel):
    """Tek nokta kara erişilebilirlik sınıflandırma sonucu"""
    input: Dict[str, float] = Field(..., description="Girdi koordinatları")
    nearest_cell: Dict[str, float] = Field(..., description="En yakın grid hücresi merkezi")
    distance_to_cell_km: float = Field(..., description="Girdi ile hücre merkezi arası mesafe (km)")
    ground_access_class: GroundAccessClass
    ground_access_score: int = Field(..., ge=0, le=3)
    dist_to_road_m: Optional[float]
    slope_deg: Optional[float]
    color: str


# ---------------------------------------------------------------------------
# Integrated Risk-Accessibility
# ---------------------------------------------------------------------------

class IntegratedAccessibilityPoint(BaseModel):
    """Yangın riski + kara erişilebilirlik birleşik hücre bilgisi"""
    center_lat: float
    center_lon: float

    # Yangın riski
    fire_risk_class: FireRiskClass
    fire_probability: float = Field(..., ge=0, le=1)
    high_fire_probability: float = Field(..., ge=0, le=1)
    combined_risk_score: float = Field(..., ge=0, le=1)

    # Kara erişilebilirlik
    ground_access_class: GroundAccessClass
    ground_access_score: int = Field(..., ge=0, le=3)
    dist_to_road_m: Optional[float]
    slope_deg: Optional[float]

    # Karar
    air_access_required: bool = Field(
        ...,
        description="True → kara erişimi yok/zayıf VE yüksek/orta yangın riski",
    )
    priority_level: PriorityLevel
    color: str = Field(..., description="Öncelik seviyesine göre renk kodu")

    model_config = {
        "json_schema_extra": {
            "example": {
                "center_lat": 38.35,
                "center_lon": 27.10,
                "fire_risk_class": "HIGH_RISK",
                "fire_probability": 0.82,
                "high_fire_probability": 0.75,
                "combined_risk_score": 0.79,
                "ground_access_class": "NO_ACCESS",
                "ground_access_score": 0,
                "dist_to_road_m": None,
                "slope_deg": 42.0,
                "air_access_required": True,
                "priority_level": "CRITICAL",
                "color": "#8b0000",
            }
        }
    }


class IntegratedSummaryResponse(BaseModel):
    """Entegre risk-erişilebilirlik özet istatistikleri"""
    total_cells: int
    fire_risk_distribution: Dict[str, int] = Field(
        ..., description="Yangın riski sınıfı başına hücre sayısı"
    )
    ground_access_distribution: Dict[str, int] = Field(
        ..., description="Kara erişim sınıfı başına eşleşen hücre sayısı"
    )
    critical_zones_count: int = Field(
        ..., description="Kritik bölge sayısı (HIGH_RISK + NO_ACCESS)"
    )
    air_only_access_count: int = Field(
        ..., description="Sadece hava ile erişilebilen yüksek/orta risk alanı sayısı"
    )
    joint_high_risk_no_access: int = Field(
        ..., description="HIGH_RISK + NO_ACCESS kombinasyon sayısı"
    )


class AccessibilityLevelInfo(BaseModel):
    """Erişilebilirlik sınıf tanım bilgisi"""
    access_class: str
    score: int
    color: str
    description: str
    criteria: Dict[str, Any]


class PriorityMatrixEntry(BaseModel):
    """Öncelik matrisi satırı"""
    fire_risk: str
    ground_access: str
    priority: str
    air_required: bool


class AccessibilityLevelsResponse(BaseModel):
    """Erişilebilirlik sınıf ve öncelik matrisi referans yanıtı"""
    ground_access_classes: List[AccessibilityLevelInfo]
    priority_matrix: List[PriorityMatrixEntry]
