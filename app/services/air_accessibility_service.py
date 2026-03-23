"""
Hava Erişilebilirliği Sınıflandırma Servisi (LLF-2.3)

Kara erişimi bulunmayan yangın risk bölgelerinin hava araçları (helikopter, uçak)
açısından erişilebilirliğini değerlendirir.
"""
import math
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
import json
from pathlib import Path


class AirAccessibilityLevel(str, Enum):
    """Hava erişilebilirlik seviyeleri"""
    EXCELLENT = "EXCELLENT"  # Mükemmel: Her türlü hava aracı kolayca erişebilir
    GOOD = "GOOD"           # İyi: Hava araçları güvenli şekilde erişebilir
    MODERATE = "MODERATE"   # Orta: Belirli kısıtlamalarla erişilebilir
    DIFFICULT = "DIFFICULT" # Zor: Sadece deneyimli pilotlar erişebilir
    RESTRICTED = "RESTRICTED"  # Kısıtlı: Çok sınırlı erişim


class AircraftType(str, Enum):
    """Hava aracı tipleri"""
    HELICOPTER = "HELICOPTER"  # Helikopter
    FIXED_WING = "FIXED_WING"  # Sabit kanatlı uçak
    DRONE = "DRONE"            # İHA/Drone


class TerrainType(str, Enum):
    """Arazi tipleri"""
    FLAT = "FLAT"              # Düz arazi
    HILLY = "HILLY"            # Tepeli arazi
    MOUNTAINOUS = "MOUNTAINOUS"  # Dağlık arazi
    FOREST = "FOREST"          # Ormanlık alan
    WATER = "WATER"            # Su üzeri


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    İki coğrafi nokta arasındaki mesafeyi km cinsinden hesaplar (Haversine formülü)
    """
    R = 6371  # Dünya yarıçapı (km)
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


class AirAccessibilityService:
    """Hava erişilebilirlik değerlendirme servisi"""
    
    # İzmir bölgesi için yaklaşık hava üsleri/havaalanları
    AIR_BASES = [
        {"name": "Adnan Menderes Havalimanı", "lat": 38.2924, "lon": 27.1570, "type": "airport"},
        {"name": "Çiğli Hava Üssü", "lat": 38.5130, "lon": 27.0100, "type": "military"},
        {"name": "İzmir Körfez Heliport", "lat": 38.4192, "lon": 27.1287, "type": "heliport"},
    ]
    
    # Helikopter menzil ve hız parametreleri
    HELICOPTER_RANGE_KM = 600  # Ortalama menzil
    HELICOPTER_SPEED_KMH = 220  # Ortalama hız
    
    # Uçak menzil ve hız parametreleri
    FIXED_WING_RANGE_KM = 2000
    FIXED_WING_SPEED_KMH = 400
    
    # Drone parametreleri
    DRONE_RANGE_KM = 50
    DRONE_SPEED_KMH = 80
    
    def __init__(self):
        """Servisi başlat ve gerekli verileri yükle"""
        self.water_sources = self._load_water_sources()
    
    def _load_water_sources(self) -> List[Dict]:
        """Su kaynaklarını yükle (acil durum iniş noktaları)"""
        base_path = Path(__file__).parent.parent.parent / "static" / "data"
        water_sources = []
        
        # Barajlar, göller vb. geniş su yüzeyleri potansiyel helikopter iniş noktası
        files = ["barajlar.geojson", "ponds-lakes.geojson", "water-reservoirs.geojson"]
        
        for file in files:
            file_path = base_path / file
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'features' in data:
                            water_sources.extend(data['features'])
                except Exception as e:
                    print(f"Su kaynağı dosyası yüklenemedi {file}: {e}")
        
        return water_sources
    
    def classify_air_accessibility(
        self,
        latitude: float,
        longitude: float,
        elevation: float = 0,
        terrain_type: TerrainType = TerrainType.FLAT,
        vegetation_density: float = 0.5,  # 0-1 arası, yoğunluk
        aircraft_type: AircraftType = AircraftType.HELICOPTER
    ) -> Dict[str, Any]:
        """
        Bir yangın risk noktasının hava erişilebilirliğini sınıflandırır
        
        Args:
            latitude: Enlem
            longitude: Boylam
            elevation: Rakım (metre)
            terrain_type: Arazi tipi
            vegetation_density: Bitki örtüsü yoğunluğu (0: açık, 1: çok yoğun)
            aircraft_type: Hava aracı tipi
        
        Returns:
            Erişilebilirlik değerlendirme sonucu
        """
        # En yakın hava üssüne mesafe
        nearest_base = self._find_nearest_air_base(latitude, longitude)
        distance_to_base = nearest_base['distance']
        
        # Menzil kontrolü
        max_range = self._get_max_range(aircraft_type)
        if distance_to_base > max_range:
            return {
                "accessibility_level": AirAccessibilityLevel.RESTRICTED,
                "score": 0,
                "distance_to_base_km": round(distance_to_base, 2),
                "nearest_base": nearest_base['name'],
                "eta_minutes": None,
                "reason": f"Menzil dışında: {round(distance_to_base, 2)}km > {max_range}km",
                "recommendations": ["Drone kullanımı düşünülebilir", "Alternatif erişim yolları araştırılmalı"]
            }
        
        # Skor hesaplama (0-100)
        score = 100
        reasons = []
        recommendations = []
        
        # 1. Mesafe faktörü (-0 ile -40 arası)
        distance_penalty = min(40, (distance_to_base / max_range) * 40)
        score -= distance_penalty
        
        # 2. Rakım faktörü (-0 ile -20 arası)
        if elevation > 1500:
            elevation_penalty = min(20, ((elevation - 1500) / 1000) * 20)
            score -= elevation_penalty
            reasons.append(f"Yüksek rakım: {elevation}m")
            recommendations.append("Deneyimli pilot gerekebilir")
        
        # 3. Arazi tipi faktörü
        terrain_penalties = {
            TerrainType.FLAT: 0,
            TerrainType.HILLY: 5,
            TerrainType.MOUNTAINOUS: 15,
            TerrainType.FOREST: 10,
            TerrainType.WATER: -5  # Su üzeri aslında avantaj
        }
        terrain_penalty = terrain_penalties.get(terrain_type, 0)
        score -= terrain_penalty
        if terrain_penalty > 0:
            reasons.append(f"Zorlu arazi: {terrain_type.value}")
        
        # 4. Bitki örtüsü faktörü (-0 ile -15 arası)
        vegetation_penalty = vegetation_density * 15
        score -= vegetation_penalty
        if vegetation_density > 0.7:
            reasons.append(f"Yoğun bitki örtüsü: {int(vegetation_density*100)}%")
            recommendations.append("İniş alanı temizliği gerekebilir")
        
        # 5. Yakın su kaynağı kontrolü (acil durum iniş noktası) (+5 bonus)
        nearest_water = self._find_nearest_water_source(latitude, longitude)
        if nearest_water and nearest_water['distance'] < 5:  # 5km içinde
            score += 5
            recommendations.append(f"Acil iniş noktası yakında: {nearest_water['name']}")
        
        # 6. Hava aracı tipine göre uygunluk
        if aircraft_type == AircraftType.FIXED_WING:
            # Sabit kanatlı uçaklar düz araziye ihtiyaç duyar
            if terrain_type in [TerrainType.MOUNTAINOUS, TerrainType.FOREST]:
                score -= 25
                reasons.append("Sabit kanatlı uçak için uygun değil")
                recommendations.append("Helikopter kullanımı önerilir")
        
        # Skoru 0-100 aralığında tut
        score = max(0, min(100, score))
        
        # Erişilebilirlik seviyesi belirleme
        accessibility_level = self._determine_accessibility_level(score)
        
        # Tahmini varış süresi (dakika)
        speed = self._get_speed(aircraft_type)
        eta_minutes = (distance_to_base / speed) * 60
        
        return {
            "accessibility_level": accessibility_level,
            "score": round(score, 1),
            "distance_to_base_km": round(distance_to_base, 2),
            "nearest_base": nearest_base['name'],
            "eta_minutes": round(eta_minutes, 1),
            "aircraft_type": aircraft_type.value,
            "terrain_type": terrain_type.value,
            "elevation_m": elevation,
            "vegetation_density": vegetation_density,
            "reasons": reasons if reasons else ["Optimal koşullar"],
            "recommendations": recommendations if recommendations else ["Standart yaklaşım uygulanabilir"],
            "nearest_water_source": nearest_water['name'] if nearest_water else None,
            "water_distance_km": round(nearest_water['distance'], 2) if nearest_water else None
        }
    
    def _find_nearest_air_base(self, lat: float, lon: float) -> Dict[str, Any]:
        """En yakın hava üssünü bulur"""
        nearest = None
        min_distance = float('inf')
        
        for base in self.AIR_BASES:
            distance = haversine_distance(lat, lon, base['lat'], base['lon'])
            if distance < min_distance:
                min_distance = distance
                nearest = {
                    'name': base['name'],
                    'type': base['type'],
                    'distance': distance,
                    'lat': base['lat'],
                    'lon': base['lon']
                }
        
        return nearest
    
    def _find_nearest_water_source(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """En yakın su kaynağını bulur (acil iniş noktası)"""
        if not self.water_sources:
            return None
        
        nearest = None
        min_distance = float('inf')
        
        for feature in self.water_sources:
            # GeoJSON koordinat formatı: [lon, lat]
            if feature.get('geometry', {}).get('type') == 'Point':
                coords = feature['geometry']['coordinates']
                water_lon, water_lat = coords[0], coords[1]
                
                distance = haversine_distance(lat, lon, water_lat, water_lon)
                if distance < min_distance:
                    min_distance = distance
                    name = feature.get('properties', {}).get('name', 'İsimsiz su kaynağı')
                    nearest = {
                        'name': name,
                        'distance': distance,
                        'lat': water_lat,
                        'lon': water_lon
                    }
        
        return nearest
    
    def _get_max_range(self, aircraft_type: AircraftType) -> float:
        """Hava aracı tipine göre maksimum menzili döndürür"""
        ranges = {
            AircraftType.HELICOPTER: self.HELICOPTER_RANGE_KM,
            AircraftType.FIXED_WING: self.FIXED_WING_RANGE_KM,
            AircraftType.DRONE: self.DRONE_RANGE_KM
        }
        return ranges.get(aircraft_type, self.HELICOPTER_RANGE_KM)
    
    def _get_speed(self, aircraft_type: AircraftType) -> float:
        """Hava aracı tipine göre ortalama hızı döndürür (km/h)"""
        speeds = {
            AircraftType.HELICOPTER: self.HELICOPTER_SPEED_KMH,
            AircraftType.FIXED_WING: self.FIXED_WING_SPEED_KMH,
            AircraftType.DRONE: self.DRONE_SPEED_KMH
        }
        return speeds.get(aircraft_type, self.HELICOPTER_SPEED_KMH)
    
    def _determine_accessibility_level(self, score: float) -> AirAccessibilityLevel:
        """Skordan erişilebilirlik seviyesi belirler"""
        if score >= 85:
            return AirAccessibilityLevel.EXCELLENT
        elif score >= 70:
            return AirAccessibilityLevel.GOOD
        elif score >= 50:
            return AirAccessibilityLevel.MODERATE
        elif score >= 30:
            return AirAccessibilityLevel.DIFFICULT
        else:
            return AirAccessibilityLevel.RESTRICTED
    
    def batch_classify(
        self,
        locations: List[Dict[str, float]],
        aircraft_type: AircraftType = AircraftType.HELICOPTER
    ) -> List[Dict[str, Any]]:
        """
        Birden fazla lokasyon için toplu erişilebilirlik sınıflandırması
        
        Args:
            locations: Liste [{"lat": x, "lon": y, "elevation": z, ...}, ...]
            aircraft_type: Hava aracı tipi
        
        Returns:
            Her lokasyon için erişilebilirlik sonuçları
        """
        results = []
        
        for loc in locations:
            result = self.classify_air_accessibility(
                latitude=loc['lat'],
                longitude=loc['lon'],
                elevation=loc.get('elevation', 0),
                terrain_type=TerrainType(loc.get('terrain_type', 'FLAT')),
                vegetation_density=loc.get('vegetation_density', 0.5),
                aircraft_type=aircraft_type
            )
            result['location'] = {'lat': loc['lat'], 'lon': loc['lon']}
            results.append(result)
        
        return results
    
    def get_accessibility_map(
        self,
        bbox: Tuple[float, float, float, float],  # (min_lon, min_lat, max_lon, max_lat)
        grid_size: float = 0.01,  # ~1km çözünürlük
        aircraft_type: AircraftType = AircraftType.HELICOPTER
    ) -> Dict[str, Any]:
        """
        Bir bölge için grid tabanlı erişilebilirlik haritası oluşturur
        
        Args:
            bbox: Bounding box (min_lon, min_lat, max_lon, max_lat)
            grid_size: Grid hücre boyutu (derece cinsinden)
            aircraft_type: Hava aracı tipi
        
        Returns:
            Grid noktalarda erişilebilirlik değerlendirmesi
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        
        grid_points = []
        lat = min_lat
        while lat <= max_lat:
            lon = min_lon
            while lon <= max_lon:
                grid_points.append({'lat': lat, 'lon': lon})
                lon += grid_size
            lat += grid_size
        
        results = self.batch_classify(grid_points, aircraft_type)
        
        # GeoJSON formatına dönüştür
        features = []
        for result in results:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [result['location']['lon'], result['location']['lat']]
                },
                "properties": {
                    "accessibility_level": result['accessibility_level'],
                    "score": result['score'],
                    "distance_to_base_km": result['distance_to_base_km'],
                    "eta_minutes": result['eta_minutes'],
                    "aircraft_type": result['aircraft_type']
                }
            }
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "aircraft_type": aircraft_type.value,
                "grid_size": grid_size,
                "total_points": len(features)
            }
        }
