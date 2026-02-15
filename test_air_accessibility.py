#!/usr/bin/env python3
"""
Hava Erişilebilirliği Sınıflandırma Test Scripti
"""
from app.services.air_accessibility_service import (
    AirAccessibilityService,
    AircraftType,
    TerrainType
)

def test_air_accessibility():
    """Hava erişilebilirlik sistemini test eder"""
    
    print("=" * 60)
    print("HAVA ERİŞİLEBİLİRLİK SINIFLANDIRMA SİSTEMİ TEST")
    print("=" * 60)
    print()
    
    # Servis instance
    service = AirAccessibilityService()
    
    # Test senaryoları
    test_locations = [
        {
            "name": "İzmir Körfez Merkez (Düz arazi)",
            "lat": 38.4192,
            "lon": 27.1287,
            "elevation": 50,
            "terrain": TerrainType.FLAT,
            "vegetation": 0.3
        },
        {
            "name": "Bornova Tepeleri (Orta yükseklik)",
            "lat": 38.4600,
            "lon": 27.2200,
            "elevation": 300,
            "terrain": TerrainType.HILLY,
            "vegetation": 0.6
        },
        {
            "name": "Karaburun Dağları (Dağlık arazi)",
            "lat": 38.6500,
            "lon": 26.5200,
            "elevation": 800,
            "terrain": TerrainType.MOUNTAINOUS,
            "vegetation": 0.7
        },
        {
            "name": "Ödemiş Ormanlık Alan",
            "lat": 38.2300,
            "lon": 27.9700,
            "elevation": 400,
            "terrain": TerrainType.FOREST,
            "vegetation": 0.9
        }
    ]
    
    aircraft_types = [AircraftType.HELICOPTER, AircraftType.FIXED_WING, AircraftType.DRONE]
    
    for aircraft in aircraft_types:
        print(f"\n{'='*60}")
        print(f"ARAÇ TİPİ: {aircraft.value}")
        print(f"{'='*60}\n")
        
        for location in test_locations:
            print(f"📍 {location['name']}")
            print(f"   Koordinat: ({location['lat']:.4f}, {location['lon']:.4f})")
            print(f"   Rakım: {location['elevation']}m | Arazi: {location['terrain'].value}")
            print()
            
            result = service.classify_air_accessibility(
                latitude=location['lat'],
                longitude=location['lon'],
                elevation=location['elevation'],
                terrain_type=location['terrain'],
                vegetation_density=location['vegetation'],
                aircraft_type=aircraft
            )
            
            # Icon belirleme
            icons = {
                'EXCELLENT': '✅',
                'GOOD': '👍',
                'MODERATE': '⚠️',
                'DIFFICULT': '⛔',
                'RESTRICTED': '🚫'
            }
            icon = icons.get(result['accessibility_level'], '❓')
            
            print(f"   {icon} ERİŞİLEBİLİRLİK: {result['accessibility_level']}")
            print(f"   📊 Skor: {result['score']}/100")
            print(f"   ✈️  En Yakın Üs: {result['nearest_base']}")
            print(f"   📏 Mesafe: {result['distance_to_base_km']} km")
            
            if result.get('eta_minutes'):
                print(f"   ⏱️  Tahmini Varış: {result['eta_minutes']:.1f} dakika")
            
            if result.get('nearest_water_source'):
                print(f"   💧 Acil İniş: {result['nearest_water_source']} ({result['water_distance_km']:.1f} km)")
            
            if result.get('reason'):
                print(f"   ⚠️  {result['reason']}")
            
            if result.get('reasons'):
                print(f"   📝 Faktörler: {', '.join(result['reasons'])}")
            
            if result.get('recommendations'):
                print(f"   💡 Öneriler:")
                for rec in result['recommendations']:
                    print(f"      • {rec}")
            
            print()
    
    # Toplu değerlendirme örneği
    print("\n" + "="*60)
    print("TOPLU DEĞERLENDİRME ÖRNEĞİ (Helikopter)")
    print("="*60 + "\n")
    
    batch_locations = [
        {"lat": loc['lat'], "lon": loc['lon'], "elevation": loc['elevation'], 
         "terrain_type": loc['terrain'].value, "vegetation_density": loc['vegetation']}
        for loc in test_locations
    ]
    
    batch_results = service.batch_classify(batch_locations, AircraftType.HELICOPTER)
    
    # En iyi ve en kötü erişilebilirliği bul
    best = max(batch_results, key=lambda x: x['score'])
    worst = min(batch_results, key=lambda x: x['score'])
    
    print(f"✅ EN İYİ ERİŞİLEBİLİRLİK:")
    print(f"   Skor: {best['score']}/100")
    print(f"   Seviye: {best['accessibility_level']}")
    print(f"   Mesafe: {best['distance_to_base_km']} km")
    print()
    
    print(f"🚫 EN ZOR ERİŞİLEBİLİRLİK:")
    print(f"   Skor: {worst['score']}/100")
    print(f"   Seviye: {worst['accessibility_level']}")
    print(f"   Mesafe: {worst['distance_to_base_km']} km")
    print()
    
    # İstatistikler
    avg_score = sum(r['score'] for r in batch_results) / len(batch_results)
    avg_distance = sum(r['distance_to_base_km'] for r in batch_results) / len(batch_results)
    
    print(f"📊 İSTATİSTİKLER:")
    print(f"   Ortalama Skor: {avg_score:.1f}/100")
    print(f"   Ortalama Mesafe: {avg_distance:.1f} km")
    print()
    
    print("="*60)
    print("TEST TAMAMLANDI! ✓")
    print("="*60)

if __name__ == "__main__":
    test_air_accessibility()
