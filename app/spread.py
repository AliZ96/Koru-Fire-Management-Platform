# app/spread.py
# Facade: gerçek iş mantığı app.services.spread_service içinde tutuluyor.
from .services.spread_service import meters_to_deg, make_spread_sector

__all__ = ["meters_to_deg", "make_spread_sector"]
