"""Facade: gerçek iş mantığı app.services.weather_service içinde tutuluyor.

Diğer modüller doğrudan `from app.services.weather_service import ...` olarak
güncellenebilir; bu dosya eski importları bozmamak için minimal re-export sağlar.
"""
from .services.weather_service import get_hourly_weather, get_wind

__all__ = ["get_hourly_weather", "get_wind"]
