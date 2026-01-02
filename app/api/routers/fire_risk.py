"""
Fire Risk API Router
Handles fire risk zones clustering and analysis endpoints
"""
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import numpy as np
from sklearn.cluster import DBSCAN

router = APIRouter(prefix="/fire-risk", tags=["fire-risk"])


def _cluster_to_zones(
    points: List[Dict[str, Any]],
    eps_km: float = 5.0,
    min_samples: int = 3,
    min_cluster_size: int = 5
) -> List[Dict[str, Any]]:
    """
    Cluster points into risk zones using DBSCAN
    
    Args:
        points: List of points with lat, lon, risk_score
        eps_km: Epsilon in kilometers
        min_samples: Min samples for DBSCAN
        min_cluster_size: Minimum size for a cluster to be a zone
        
    Returns:
        List of risk zones with bbox and average risk
    """
    if not points:
        return []
    
    # Extract coordinates
    coords = np.array([[p["lat"], p["lon"]] for p in points])
    risks = np.array([p["risk_score"] for p in points])
    
    # Convert km to degrees (approximate)
    eps_deg = eps_km / 111.0
    
    # Perform clustering
    clustering = DBSCAN(eps=eps_deg, min_samples=min_samples).fit(coords)
    labels = clustering.labels_
    
    # Build zones
    zones = []
    unique_labels = set(labels)
    
    for label in sorted(unique_labels):
        if label == -1:  # Skip noise points
            continue
        
        mask = labels == label
        cluster_coords = coords[mask]
        cluster_risks = risks[mask]
        
        # Only keep zones with minimum size
        if np.sum(mask) >= min_cluster_size:
            zone = {
                "zone_id": len(zones),
                "bbox": [
                    float(cluster_coords[:, 0].min()),
                    float(cluster_coords[:, 1].min()),
                    float(cluster_coords[:, 0].max()),
                    float(cluster_coords[:, 1].max()),
                ],
                "avg_risk": float(cluster_risks.mean()),
                "count": int(np.sum(mask))
            }
            zones.append(zone)
    
    return zones


@router.get("/zones")
def get_zones(
    eps_km: float = Query(5.0, ge=0.1),
    min_samples: int = Query(3, ge=1),
    min_cluster_size: int = Query(5, ge=1),
    limit: int = Query(1000, ge=1, le=10000)
) -> JSONResponse:
    """Get clustered risk zones"""
    # Mock data - replace with real data source
    mock_points = [
        {"lat": 38.5, "lon": 27.2, "risk_score": 0.8},
        {"lat": 38.501, "lon": 27.201, "risk_score": 0.75},
        {"lat": 38.502, "lon": 27.202, "risk_score": 0.78},
        {"lat": 39.0, "lon": 28.0, "risk_score": 0.3},
    ]
    
    zones = _cluster_to_zones(
        mock_points,
        eps_km=eps_km,
        min_samples=min_samples,
        min_cluster_size=min_cluster_size
    )
    
    return JSONResponse({
        "zones": zones[:limit],
        "total": len(zones)
    })


@router.get("/zones/top")
def get_top_zones(
    n: int = Query(5, ge=1, le=100),
    eps_km: float = Query(5.0, ge=0.1),
    min_samples: int = Query(3, ge=1),
    min_cluster_size: int = Query(5, ge=1)
) -> JSONResponse:
    """Get top N highest risk zones"""
    # Mock data
    mock_points = [
        {"lat": 38.5, "lon": 27.2, "risk_score": 0.9},
        {"lat": 38.501, "lon": 27.201, "risk_score": 0.85},
        {"lat": 38.502, "lon": 27.202, "risk_score": 0.88},
        {"lat": 39.0, "lon": 28.0, "risk_score": 0.2},
        {"lat": 39.5, "lon": 28.5, "risk_score": 0.6},
    ]
    
    zones = _cluster_to_zones(
        mock_points,
        eps_km=eps_km,
        min_samples=min_samples,
        min_cluster_size=min_cluster_size
    )
    
    # Sort by average risk
    zones_sorted = sorted(zones, key=lambda z: z["avg_risk"], reverse=True)
    
    return JSONResponse({
        "zones": zones_sorted[:n],
        "total": len(zones)
    })


@router.get("/points")
def get_points(limit: int = Query(100, ge=1, le=10000)) -> JSONResponse:
    """Get fire risk points"""
    mock_points = [
        {"lat": 38.5, "lon": 27.2, "risk_score": 0.8},
        {"lat": 38.501, "lon": 27.201, "risk_score": 0.75},
        {"lat": 39.0, "lon": 28.0, "risk_score": 0.3},
    ]
    
    return JSONResponse({
        "points": mock_points[:limit]
    })


@router.get("/heatmap-data")
def get_heatmap_data(limit: int = Query(100, ge=1, le=10000)) -> JSONResponse:
    """Get heatmap data [lat, lon, intensity]"""
    mock_data = [
        [38.5, 27.2, 0.8],
        [38.501, 27.201, 0.75],
        [39.0, 28.0, 0.3],
    ]
    
    return mock_data[:limit]


@router.get("/statistics")
def get_statistics() -> JSONResponse:
    """Get risk statistics"""
    return JSONResponse({
        "total_points": 1000,
        "high_risk_zones": 5,
        "avg_risk": 0.45,
        "last_update": "2024-01-02T00:00:00Z"
    })
