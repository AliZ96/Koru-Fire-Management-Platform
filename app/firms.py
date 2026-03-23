# Facade: gerçek iş mantığı app.services.firms_service içinde tutuluyor.
from .services.firms_service import fetch_firms_geojson

__all__ = ["fetch_firms_geojson"]