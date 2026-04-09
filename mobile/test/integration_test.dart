import 'package:flutter_test/flutter_test.dart';
import 'package:latlong2/latlong.dart';
import 'package:koru_app/models/accessibility_data.dart';
import 'package:koru_app/services/api_service.dart';
import 'package:koru_app/services/map_data_service.dart';

void main() {
  group('API Integration Tests', () {
    late ApiService apiService;
    late MapDataService mapDataService;

    setUp(() {
      apiService = ApiService();
      mapDataService = MapDataService(apiService);
    });

    test('ApiService initialization', () {
      expect(apiService, isNotNull);
      expect(apiService.baseUrl, isNotEmpty);
    });

    test('MapDataService initialization', () {
      expect(mapDataService, isNotNull);
      expect(mapDataService.loadingRiskZones, isFalse);
      expect(mapDataService.loadingAccessibility, isFalse);
      expect(mapDataService.riskZones, isEmpty);
    });

    test('Risk Zone model creation from JSON', () {
      final json = {
        'bbox': [27.0, 38.0, 28.0, 39.0],
        'avg_risk': 0.65,
        'count': 25,
        'risk_class': 'HIGH_RISK',
      };

      final zone = RiskZone.fromJson(json);

      expect(zone, isNotNull);
      expect(zone.riskClass, equals('HIGH_RISK'));
      expect(zone.avgRiskScore, equals(0.65));
      expect(zone.pointCount, equals(25));
      expect(zone.riskLabel, equals('Yüksek Risk'));
    });

    test('Accessibility Zone model creation from GeoJSON', () {
      final feature = {
        'type': 'Feature',
        'geometry': {
          'type': 'Point',
          'coordinates': [27.14, 38.42],
        },
        'properties': {
          'accessibility_class': 'HIGH',
          'accessibility': 0.85,
          'point_count': 150,
        },
      };

      final zone = AccessibilityZone.fromGeoJsonFeature(feature);

      expect(zone, isNotNull);
      expect(zone.accessibilityClass, equals('HIGH'));
      expect(zone.accessibility, equals(0.85));
      expect(zone.pointCount, equals(150));
      expect(zone.accessibilityLabel, equals('Yüksek Erişilebilirlik'));
    });

    test('Risk Statistics model creation', () {
      final json = {
        'total_points': 5000,
        'average_fire_probability': 0.25,
        'average_combined_risk_score': 0.50,
        'high_risk_count': 500,
        'medium_risk_count': 1500,
        'low_risk_count': 2000,
        'safe_count': 1000,
        'risk_distribution': {'HIGH_RISK': 500, 'MEDIUM_RISK': 1500},
      };

      final stats = FireRiskStatistics.fromJson(json);

      expect(stats, isNotNull);
      expect(stats.totalPoints, equals(5000));
      expect(stats.highRiskCount, equals(500));
      expect(stats.averageFireProbability, equals(0.25));
    });

    test('Integrated Zone model creation', () {
      final feature = {
        'type': 'Feature',
        'geometry': {
          'type': 'Point',
          'coordinates': [27.14, 38.42],
        },
        'properties': {
          'risk_class': 'HIGH_RISK',
          'accessibility_class': 'LOW',
          'combined_score': 0.75,
          'point_count': 50,
        },
      };

      final zone = IntegratedZone.fromGeoJsonFeature(feature);

      expect(zone, isNotNull);
      expect(zone.riskClass, equals('HIGH_RISK'));
      expect(zone.accessibilityClass, equals('LOW'));
      expect(zone.combinedScore, equals(0.75));
      expect(zone.pointCount, equals(50));
    });

    test('API Error model creation', () {
      final error = ApiError(
        message: 'Network error',
        statusCode: 500,
        originalError: Exception('Connection failed'),
      );

      expect(error, isNotNull);
      expect(error.message, equals('Network error'));
      expect(error.statusCode, equals(500));
      expect(error.toString(), contains('ApiError'));
    });

    test('Risk Zone color assignment by risk class', () {
      final highRiskZone = RiskZone(
        center: const LatLng(38.42, 27.14),
        riskClass: 'HIGH_RISK',
        avgRiskScore: 0.9,
        pointCount: 100,
        bbox: [27.0, 38.0, 28.0, 39.0],
      );

      final mediumRiskZone = RiskZone(
        center: const LatLng(38.42, 27.14),
        riskClass: 'MEDIUM_RISK',
        avgRiskScore: 0.6,
        pointCount: 150,
        bbox: [27.0, 38.0, 28.0, 39.0],
      );

      expect(highRiskZone.colorFromRisk, isNotNull);
      expect(mediumRiskZone.colorFromRisk, isNotNull);
      expect(
        highRiskZone.colorFromRisk != mediumRiskZone.colorFromRisk,
        isTrue,
      );
    });

    test('Accessibility Zone color assignment by accessibility class', () {
      final highAccessZone = AccessibilityZone(
        center: const LatLng(38.42, 27.14),
        accessibilityClass: 'HIGH',
        accessibility: 0.9,
        pointCount: 100,
      );

      final noAccessZone = AccessibilityZone(
        center: const LatLng(38.42, 27.14),
        accessibilityClass: 'NO_ACCESS',
        accessibility: 0.0,
        pointCount: 50,
      );

      expect(highAccessZone.colorFromAccessibility, isNotNull);
      expect(noAccessZone.colorFromAccessibility, isNotNull);
      expect(
        highAccessZone.colorFromAccessibility !=
            noAccessZone.colorFromAccessibility,
        isTrue,
      );
    });
  });
}
