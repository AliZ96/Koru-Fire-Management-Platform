import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';
import '../models/accessibility_data.dart';
import '../models/fire_data.dart';
import 'api_service.dart';

/// Service for managing map data retrieval, transformation, and caching
class MapDataService extends ChangeNotifier {
  final ApiService apiService;

  // Cache for risk zones
  List<RiskZone> _riskZones = [];
  List<RiskZone> get riskZones => _riskZones;

  // Cache for accessibility zones
  List<AccessibilityZone> _accessibilityZones = [];
  List<AccessibilityZone> get accessibilityZones => _accessibilityZones;

  // Cache for integrated zones
  List<IntegratedZone> _integratedZones = [];
  List<IntegratedZone> get integratedZones => _integratedZones;

  // Statistics cache
  FireRiskStatistics? _statistics;
  FireRiskStatistics? get statistics => _statistics;

  // Loading states
  bool _loadingRiskZones = false;
  bool get loadingRiskZones => _loadingRiskZones;

  bool _loadingAccessibility = false;
  bool get loadingAccessibility => _loadingAccessibility;

  bool _loadingIntegrated = false;
  bool get loadingIntegrated => _loadingIntegrated;

  bool _loadingStatistics = false;
  bool get loadingStatistics => _loadingStatistics;

  // Error handling
  String? _lastError;
  String? get lastError => _lastError;

  MapDataService(this.apiService);

  /// Fetch fire risk statistics
  Future<void> loadRiskStatistics() async {
    if (_loadingStatistics) return;

    try {
      _loadingStatistics = true;
      _lastError = null;
      notifyListeners();

      final response = await apiService.getFireRiskStatistics();

      if (response.containsKey('error')) {
        _lastError = response['error'];
        return;
      }

      _statistics = FireRiskStatistics.fromJson(response);
      notifyListeners();
    } catch (e) {
      _lastError = 'İstatistik yüklenirken hata: $e';
      debugPrint('Error loading statistics: $e');
    } finally {
      _loadingStatistics = false;
      notifyListeners();
    }
  }

  /// Fetch fire risk zones and cluster them
  Future<void> loadRiskZones() async {
    if (_loadingRiskZones) return;

    try {
      _loadingRiskZones = true;
      _lastError = null;
      notifyListeners();

      // First, get all fire risk points
      final response = await apiService.getFireRiskPoints();

      if (response.containsKey('error')) {
        _lastError = response['error'];
        return;
      }

      // Parse features and cluster them into zones
      final features = response['features'] as List? ?? [];
      _riskZones = _clusterPointsIntoZones(features);

      notifyListeners();
    } catch (e) {
      _lastError = 'Risk zonları yüklenirken hata: $e';
      debugPrint('Error loading risk zones: $e');
    } finally {
      _loadingRiskZones = false;
      notifyListeners();
    }
  }

  /// Fetch ground accessibility zones
  Future<void> loadAccessibilityZones({String? accessClass}) async {
    if (_loadingAccessibility) return;

    try {
      _loadingAccessibility = true;
      _lastError = null;
      notifyListeners();

      final response = await apiService.getAccessibilityMap(
        accessClass: accessClass,
      );

      if (response.containsKey('error')) {
        _lastError = response['error'];
        return;
      }

      final features = response['features'] as List? ?? [];
      _accessibilityZones = features
          .where((f) => f is Map<String, dynamic>)
          .map(
            (f) =>
                AccessibilityZone.fromGeoJsonFeature(f as Map<String, dynamic>),
          )
          .toList();

      notifyListeners();
    } catch (e) {
      _lastError = 'Erişilebilirlik verileri yüklenirken hata: $e';
      debugPrint('Error loading accessibility: $e');
    } finally {
      _loadingAccessibility = false;
      notifyListeners();
    }
  }

  /// Fetch integrated risk-accessibility zones
  Future<void> loadIntegratedZones() async {
    if (_loadingIntegrated) return;

    try {
      _loadingIntegrated = true;
      _lastError = null;
      notifyListeners();

      final response = await apiService.getAccessibilityIntegratedMap();

      if (response.containsKey('error')) {
        _lastError = response['error'];
        return;
      }

      final features = response['features'] as List? ?? [];
      _integratedZones = features
          .where((f) => f is Map<String, dynamic>)
          .map(
            (f) => IntegratedZone.fromGeoJsonFeature(f as Map<String, dynamic>),
          )
          .toList();

      notifyListeners();
    } catch (e) {
      _lastError = 'Entegre veriler yüklenirken hata: $e';
      debugPrint('Error loading integrated zones: $e');
    } finally {
      _loadingIntegrated = false;
      notifyListeners();
    }
  }

  /// Cluster fire risk points into zones
  List<RiskZone> _clusterPointsIntoZones(List<dynamic> features) {
    final zones = <String, List<Map<String, dynamic>>>{};
    final points = <Map<String, dynamic>>[];

    // Parse features and group by risk class
    for (final feature in features) {
      if (feature is! Map<String, dynamic>) continue;

      final geometry = feature['geometry'] as Map<String, dynamic>? ?? {};
      final properties = feature['properties'] as Map<String, dynamic>? ?? {};

      if (geometry['type'] == 'Point') {
        final coords = geometry['coordinates'] as List? ?? [];
        if (coords.length < 2) continue;

        final point = {
          'lat': (coords[1] as num).toDouble(),
          'lon': (coords[0] as num).toDouble(),
          'risk_class':
              properties['risk_class']?.toString() ?? 'SAFE_UNBURNABLE',
          'risk_score':
              (properties['combined_risk_score'] as num?)?.toDouble() ?? 0.0,
        };

        points.add(point);

        final riskClass = point['risk_class'] as String;
        zones.putIfAbsent(riskClass, () => []).add(point);
      }
    }

    // Convert zones to RiskZone objects
    final result = <RiskZone>[];
    zones.forEach((riskClass, zonePoints) {
      if (zonePoints.isEmpty) return;

      final lats = zonePoints.map((p) => (p['lat'] as num).toDouble()).toList();
      final lons = zonePoints.map((p) => (p['lon'] as num).toDouble()).toList();
      final scores = zonePoints
          .map((p) => (p['risk_score'] as num).toDouble())
          .toList();

      final centerLat = lats.reduce((a, b) => a + b) / lats.length;
      final centerLon = lons.reduce((a, b) => a + b) / lons.length;
      final avgScore = scores.reduce((a, b) => a + b) / scores.length;

      result.add(
        RiskZone(
          center: LatLng(centerLat, centerLon),
          riskClass: riskClass,
          avgRiskScore: avgScore,
          pointCount: zonePoints.length,
          bbox: [
            lons.reduce((a, b) => a < b ? a : b),
            lats.reduce((a, b) => a < b ? a : b),
            lons.reduce((a, b) => a > b ? a : b),
            lats.reduce((a, b) => a > b ? a : b),
          ],
        ),
      );
    });

    return result;
  }

  /// Get accessibility level definitions
  Future<List<AccessibilityLevel>> getAccessibilityLevels() async {
    try {
      final response = await apiService.getAccessibilityLevels();

      if (response.containsKey('error')) {
        _lastError = response['error'];
        return [];
      }

      final levelsData = response['levels'] as List? ?? [];
      return levelsData
          .where((l) => l is Map<String, dynamic>)
          .map((l) => AccessibilityLevel.fromJson(l as Map<String, dynamic>))
          .toList();
    } catch (e) {
      _lastError = 'Erişilebilirlik seviyeleri yüklenirken hata: $e';
      debugPrint('Error loading accessibility levels: $e');
      return [];
    }
  }

  /// Filter risk zones by risk class
  List<RiskZone> filterRiskZonesByClass(String riskClass) {
    return _riskZones.where((zone) => zone.riskClass == riskClass).toList();
  }

  /// Filter accessibility zones by accessibility class
  List<AccessibilityZone> filterAccessibilityByClass(String accessClass) {
    return _accessibilityZones
        .where((zone) => zone.accessibilityClass == accessClass)
        .toList();
  }

  /// Clear all cached data
  void clearCache() {
    _riskZones = [];
    _accessibilityZones = [];
    _integratedZones = [];
    _statistics = null;
    _lastError = null;
    notifyListeners();
  }

  /// Refresh all data
  Future<void> refreshAll() async {
    clearCache();
    await Future.wait([
      loadRiskZones(),
      loadAccessibilityZones(),
      loadIntegratedZones(),
      loadRiskStatistics(),
    ]);
  }
}
