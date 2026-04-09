# Mobil Uygulamanın Backend API'ye Bağlanması - Uygulama Kılavuzu

## Özet
Koru Fire Management Platform mobil uygulaması, backend API endpoints'lerine başarıyla bağlanmış, yangın riski verilerini ve erişilebilirlik verilerini dinamik olarak alabilecek şekilde yapılandırılmıştır.

## Yapılan Değişiklikler

### 1. **Veri Modelleri** (Erişilebilirlik ve Risk Zonları)
**Dosya:** `mobile/lib/models/accessibility_data.dart`

Yeni model sınıfları oluşturuldu:
- `AccessibilityLevel` - Erişilebilirlik seviye tanımları
- `AccessibilityZone` - Kara erişilebilirlik bölgeleri
- `IntegratedZone` - Risk + Erişilebilirlik entegre bölgeler
- `RiskZone` - Yangın riski zonları
- `FireRiskStatistics` - Yangın riski istatistikleri
- `ApiError` - API hata yönetimi

Tüm modeller:
- GeoJSON özelliklerinden otomatik oluşturulabilir
- Türkçe etiketler içerir
- Renge göre görselleştirme desteği sağlar

### 2. **Harita Veri Servisi**
**Dosya:** `mobile/lib/services/map_data_service.dart`

`MapDataService` sınıfı geliştirildi:
- Risk zonları yükleme ve filtreleme
- Erişilebilirlik verilerini alma
- Entegre bölge verilerini işleme
- İstatistikler yükleme
- Nokta kümeleştirme (clustering) algoritması
- Önbellek yönetimi
- Hata yakalama ve durumu bildirim
- `ChangeNotifier` ile durumu izleme

**Temel Metodlar:**
```dart
loadRiskZones()              // Yangın risk zonlarını yükle
loadAccessibilityZones()     // Erişilebilirlik verilerini yükle
loadIntegratedZones()        // Entegre verileri yükle
loadRiskStatistics()         // İstatistikleri yükle
refreshAll()                 // Tüm verileri yenile
clearCache()                 // Önbelleği temizle
filterRiskZonesByClass()     // Risk sınıfına göre filtrele
filterAccessibilityByClass() // Erişilebilirlik sınıfına göre filtrele
```

### 3. **API Servisi Güncellemeleri**
**Dosya:** `mobile/lib/services/api_service.dart`

Yeni API endpoint metodları eklendi:
```dart
getAccessibilityMap()           // Kara erişilebilirlik haritası
getAccessibilityIntegratedMap() // Entegre harita
getAccessibilityLevels()        // Erişilebilirlik seviyeleri
```

**Ek ayarlar:**
- `mobile/lib/config/api_config.dart` güncellendi yeni endpoint'lerle

### 4. **Kullanıcı Arayüzü Bileşenleri**
**Dosya:** `mobile/lib/widgets/data_display_widgets.dart`

Yeni widget'lar oluşturuldu:
- `RiskDataCard` - Risk zonları görüntüleme
- `RiskZoneListTile` - Tek risk bölgesi elemanı
- `AccessibilityDataCard` - Erişilebilirlik verileri
- `AccessibilityZoneListTile` - Tek erişilebilirlik elemanı
- `RiskStatisticsCard` - İstatistikler özeti
- `_StatisticRow` - İstatistik satırı

Özellikler:
- Yükleme durumunu göster
- Hata yönetimi ve yeniden deneme düğmesi
- Veri olmadığında mesaj göster
- Renkli gösterge çalışma
- Koordinat bilgisi (tooltip)

### 5. **Veri Görselleştirme Ekranı**
**Dosya:** `mobile/lib/screens/data_visualization_screen.dart`

3 sekme ile kapsamlı veri görüntüleme:
1. **Risk Zonları Sekmesi**
   - Yüksek Risk Zonları
   - Orta Risk Zonları
   - Düşük Risk Zonları
   - Güvenli Bölgeler

2. **Erişilebilirlik Sekmesi**
   - Yüksek Erişilebilirlik Alanları
   - Orta Erişilebilirlik Alanları
   - Düşük Erişilebilirlik Alanları
   - Erişim Olmayan Alanlar

3. **İstatistikler Sekmesi**
   - Toplam noktalar
   - Risk dağılımı
   - Ortalama istatistikler
   - Ayarlar (Yenile, Önbelleği Temizle)

### 6. **Harita Ekranı Entegrasyonu**
**Dosya:** `mobile/lib/screens/map_screen.dart`

Güncellemeler:
- `MapDataService` provider'ı import edildi
- `initState` içinde veri servisi başlatıldı
- FloatingActionButton eklendi: "Veriler" düğmesi
- Veri Görselleştirme Ekranına navigasyon

### 7. **Ana Uygulama Provider'ı**
**Dosya:** `mobile/lib/main.dart`

Güncellemeler:
- `MapDataService` başlatıldı
- `ChangeNotifierProvider` olarak register edildi
- Tüm widget tree'de erişilebilir

### 8. **Test Dosyası**
**Dosya:** `mobile/test/integration_test.dart`

Kapsamlı unit test'ler:
- ApiService ve MapDataService başlatma
- Model oluşturma ve JSON parsing
- Risk Zone renk atama
- Erişilebilirlik renk atama
- İstatistik hesaplamaları
- Hata yönetimi

## API Endpoints

### Backend API Endpoints (Python/FastAPI)

```
GET /api/fire-risk/points
  - Yangın risk noktalarını GeoJSON formatında döndür
  - Query: risk_class, limit

GET /api/fire-risk/statistics
  - Yangın risk istatistiklerini döndür

GET /api/fire-risk/heatmap-data
  - Isıl harita verilerini döndür

GET /api/accessibility/ground/map
  - Kara erişilebilirlik haritasını döndür
  - Query: access_class, minLon, minLat, maxLon, maxLat

GET /api/accessibility/integrated/map
  - Risk + Erişilebilirlik entegre haritasını döndür

GET /api/accessibility/levels
  - Erişilebilirlik seviye tanımlarını döndür
```

## Kullanım Örneği

### Mobil Uygulamada Veri Yükleme

```dart
// MapDataService'i alın
final mapDataService = context.read<MapDataService>();

// Veri yükleyin
await mapDataService.loadRiskZones();
await mapDataService.loadAccessibilityZones();
await mapDataService.loadRiskStatistics();

// Verilere erişin
final riskZones = mapDataService.riskZones;
final highRiskZones = mapDataService.filterRiskZonesByClass('HIGH_RISK');
final stats = mapDataService.statistics;

// Hatalara bakın
if (mapDataService.lastError != null) {
  print('Error: ${mapDataService.lastError}');
}

// Durumu izleyin
Consumer<MapDataService>(
  builder: (context, service, _) {
    if (service.loadingRiskZones) {
      return const CircularProgressIndicator();
    }
    return Text('Risk Zones: ${service.riskZones.length}');
  },
)
```

## Hata Yönetimi ve Yükleme Durumları

### Yükleme Durumları
- `loadingRiskZones` - Risk zonları yükleniyor mu?
- `loadingAccessibility` - Erişilebilirlik verileri yükleniyor mu?
- `loadingIntegrated` - Entegre veriler yükleniyor mu?
- `loadingStatistics` - İstatistikler yükleniyor mu?

### Hata Yönetimi
- `lastError` - Son oluşan hata mesajı
- Tüm API çağrıları try-catch ile korunmuştur
- Hata mesajları Türkçedir
- UI'da hata göstergesi vardır

## Başlatma Adımları

1. **Backend'in Çalıştığından Emin Olun**
   ```bash
   cd /path/to/koru
   python -m uvicorn app.main:app --reload
   ```

2. **Mobil Uygulamayı Çalıştırın**
   ```bash
   cd mobile
   flutter pub get
   flutter run
   ```

3. **API Endpoint'lerini Kontrol Edin**
   - Tarayıcıda `http://localhost:8000/api/fire-risk/points` açın
   - Yanıt JSON formatında risk noktaları göstermelidir

4. **Mobil Uygulamada Test Edin**
   - Giriş yapın
   - Harita ekranında FAB "Veriler" düğmesine tıklayın
   - Risk zonları ve erişilebilirlik verileri yüklenmelidir

## Önemli Notlar

### API Bağlantısı İçin Yapılandırma
- Android Emulator: `10.0.2.2:8000`
- Fiziksel Cihaz: `<computer_ip>:8000`
- iOS: `localhost:8000`

### Veri Güvenliği
- Tüm API çağrıları Bearer token ile yapılır
- Token AuthService'den alınır
- 6 saniyelik timeout ayarıdır

### Performans Optimizasyonları
- Verileri ChangeNotifier ile izlenir
- Kreatif önbellek sistemi vardır
- Noktalar risk sınıfına göre kümelenmiştir
- İzmir sınırlarına göre filtrelenir

## Kabul Kriterleri ✓

- ✓ Mobil uygulama başarıyla backend'e bağlanır
- ✓ Risk verileri doğru görüntülenir
- ✓ API yanıtları hatasız parse edilir
- ✓ Mobil arayüzü verileri dinamik olarak yükler
- ✓ Veri alınırken çöküş olmaz

## Sonraki Adımlar

1. **Harita Üzerinde Gösterim**
   - Risk zonlarını harita üzerinde poligon olarak göster
   - Erişilebilirlik verilerini renk açısından katman olarak ekle
   - Tıklama ile detay göster

2. **Performans İyileştirmesi**
   - Büyük veri setleri için sayfalandırma ekle
   - Metin-tabanlı arama özelliği ekle
   - Veri indir/çevrimdışı mod

3. **İleri Filtreleme**
   - Tarih aralığına göre filtrele
   - Bounding box ile filtrele
   - Çoklu risk sınıfı seçimi

4. **Widget Geliştirmeleri**
   - Grafik ve harita entegrasyon
   - Gerçek zamanlı güncellemeler
   - Veri dışa aktarma (CSV, PDF)

## Dosya Yapısı Özeti

```
mobile/
├── lib/
│   ├── main.dart                          (MapDataService provider'ı eklendi)
│   ├── services/
│   │   ├── api_service.dart              (Erişilebilirlik endpoint'leri eklendi)
│   │   └── map_data_service.dart         (YENİ - Veri yönetimi servisi)
│   ├── models/
│   │   └── accessibility_data.dart       (YENİ - Erişilebilirlik modelleri)
│   ├── screens/
│   │   ├── map_screen.dart               (FloatingActionButton ve entegrasyon)
│   │   └── data_visualization_screen.dart (YENİ - Veri görüntüleme ekranı)
│   ├── widgets/
│   │   └── data_display_widgets.dart     (YENİ - Veri gösterme widget'ları)
│   └── config/
│       └── api_config.dart               (Erişilebilirlik endpoint'leri eklendi)
└── test/
    └── integration_test.dart             (YENİ - API entegrasyon testleri)
```

---
**Tarih:** Nisan 2026  
**Versiyon:** 1.0  
**Durum:** Tamamlandı ✓
