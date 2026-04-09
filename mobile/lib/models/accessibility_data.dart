import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';

/// Represents an accessibility classification level
class AccessibilityLevel {
  final String id;
  final String name;
  final String color;
  final int priority;

  AccessibilityLevel({
    required this.id,
    required this.name,
    required this.color,
    required this.priority,
  });

  factory AccessibilityLevel.fromJson(Map<String, dynamic> json) {
    return AccessibilityLevel(
      id: json['id']?.toString() ?? 'UNKNOWN',
      name: json['name']?.toString() ?? 'Bilinmeyen',
      color: json['color']?.toString() ?? '#95a5a6',
      priority: (json['priority'] as num?)?.toInt() ?? 0,
    );
  }
}

/// Represents a ground accessibility zone
class AccessibilityZone {
  final LatLng center;
  final String accessibilityClass;
  final double accessibility;
  final int pointCount;
  final Map<String, dynamic> properties;

  AccessibilityZone({
    required this.center,
    required this.accessibilityClass,
    required this.accessibility,
    required this.pointCount,
    this.properties = const {},
  });

  factory AccessibilityZone.fromGeoJsonFeature(Map<String, dynamic> feature) {
    final geom = feature['geometry'] as Map<String, dynamic>? ?? {};
    final props = feature['properties'] as Map<String, dynamic>? ?? {};

    double lat = 38.4237, lon = 27.1428; // Default to Izmir center

    final geomType = geom['type'] as String?;
    final coords = geom['coordinates'];

    try {
      if (geomType == 'Point' && coords is List && coords.length >= 2) {
        lon = (coords[0] as num).toDouble();
        lat = (coords[1] as num).toDouble();
      } else if (geomType == 'Polygon' && coords is List && coords.isNotEmpty) {
        final ring = coords[0] as List;
        if (ring.isNotEmpty) {
          lon =
              ring.fold<double>(0, (s, c) => s + (c[0] as num).toDouble()) /
              ring.length;
          lat =
              ring.fold<double>(0, (s, c) => s + (c[1] as num).toDouble()) /
              ring.length;
        }
      }
    } catch (_) {
      // Use default center
    }

    return AccessibilityZone(
      center: LatLng(lat, lon),
      accessibilityClass:
          props['accessibility_class']?.toString() ?? 'NO_ACCESS',
      accessibility: (props['accessibility'] as num?)?.toDouble() ?? 0.0,
      pointCount: (props['point_count'] as num?)?.toInt() ?? 0,
      properties: props,
    );
  }

  String get accessibilityLabel {
    switch (accessibilityClass) {
      case 'HIGH':
        return 'Yüksek Erişilebilirlik';
      case 'MEDIUM':
        return 'Orta Erişilebilirlik';
      case 'LOW':
        return 'Düşük Erişilebilirlik';
      case 'NO_ACCESS':
        return 'Erişim Yok';
      default:
        return accessibilityClass;
    }
  }

  Color get colorFromAccessibility {
    switch (accessibilityClass) {
      case 'HIGH':
        return const Color(0xFF2ecc71); // Yeşil
      case 'MEDIUM':
        return const Color(0xFFF39c12); // Turuncu
      case 'LOW':
        return const Color(0xFFe67e22); // Koyu turuncu
      case 'NO_ACCESS':
        return const Color(0xFF95a5a6); // Gri
      default:
        return const Color(0xFF95a5a6);
    }
  }
}

/// Integrated risk-accessibility zone
class IntegratedZone {
  final LatLng center;
  final String riskClass;
  final String accessibilityClass;
  final double combinedScore;
  final int pointCount;

  IntegratedZone({
    required this.center,
    required this.riskClass,
    required this.accessibilityClass,
    required this.combinedScore,
    required this.pointCount,
  });

  factory IntegratedZone.fromGeoJsonFeature(Map<String, dynamic> feature) {
    final geom = feature['geometry'] as Map<String, dynamic>? ?? {};
    final props = feature['properties'] as Map<String, dynamic>? ?? {};

    double lat = 38.4237, lon = 27.1428; // Default to Izmir center

    final geomType = geom['type'] as String?;
    final coords = geom['coordinates'];

    try {
      if (geomType == 'Point' && coords is List && coords.length >= 2) {
        lon = (coords[0] as num).toDouble();
        lat = (coords[1] as num).toDouble();
      } else if (geomType == 'Polygon' && coords is List && coords.isNotEmpty) {
        final ring = coords[0] as List;
        if (ring.isNotEmpty) {
          lon =
              ring.fold<double>(0, (s, c) => s + (c[0] as num).toDouble()) /
              ring.length;
          lat =
              ring.fold<double>(0, (s, c) => s + (c[1] as num).toDouble()) /
              ring.length;
        }
      }
    } catch (_) {
      // Use default center
    }

    return IntegratedZone(
      center: LatLng(lat, lon),
      riskClass: props['risk_class']?.toString() ?? 'UNKNOWN',
      accessibilityClass: props['accessibility_class']?.toString() ?? 'UNKNOWN',
      combinedScore: (props['combined_score'] as num?)?.toDouble() ?? 0.0,
      pointCount: (props['point_count'] as num?)?.toInt() ?? 0,
    );
  }
}

/// Risk zone information
class RiskZone {
  final LatLng center;
  final String riskClass;
  final double avgRiskScore;
  final int pointCount;
  final List<double> bbox; // [minLon, minLat, maxLon, maxLat]

  RiskZone({
    required this.center,
    required this.riskClass,
    required this.avgRiskScore,
    required this.pointCount,
    required this.bbox,
  });

  factory RiskZone.fromJson(Map<String, dynamic> json) {
    final bbox =
        (json['bbox'] as List?)?.map((e) => (e as num).toDouble()).toList() ??
        [0, 0, 0, 0];

    double lat = 38.4237, lon = 27.1428;
    if (bbox.length >= 4) {
      lon = (bbox[0] + bbox[2]) / 2;
      lat = (bbox[1] + bbox[3]) / 2;
    }

    return RiskZone(
      center: LatLng(lat, lon),
      riskClass: json['risk_class']?.toString() ?? 'UNKNOWN',
      avgRiskScore: (json['avg_risk'] as num?)?.toDouble() ?? 0.0,
      pointCount: (json['count'] as num?)?.toInt() ?? 0,
      bbox: bbox,
    );
  }

  String get riskLabel {
    switch (riskClass) {
      case 'HIGH_RISK':
        return 'Yüksek Risk';
      case 'MEDIUM_RISK':
        return 'Orta Risk';
      case 'LOW_RISK':
        return 'Düşük Risk';
      case 'SAFE_UNBURNABLE':
        return 'Güvenli';
      default:
        return riskClass;
    }
  }

  Color get colorFromRisk {
    switch (riskClass) {
      case 'HIGH_RISK':
        return const Color(0xFF8b0000); // Koyu kırmızı
      case 'MEDIUM_RISK':
        return const Color(0xFFe74c3c); // Kırmızı
      case 'LOW_RISK':
        return const Color(0xFFf39c12); // Turuncu
      case 'SAFE_UNBURNABLE':
        return const Color(0xFF2ecc71); // Yeşil
      default:
        return const Color(0xFF95a5a6);
    }
  }
}

/// Statistics about fire risk
class FireRiskStatistics {
  final int totalPoints;
  final Map<String, int> riskDistribution;
  final double averageFireProbability;
  final double averageCombinedRiskScore;
  final int highRiskCount;
  final int mediumRiskCount;
  final int lowRiskCount;
  final int safeCount;

  FireRiskStatistics({
    required this.totalPoints,
    required this.riskDistribution,
    required this.averageFireProbability,
    required this.averageCombinedRiskScore,
    required this.highRiskCount,
    required this.mediumRiskCount,
    required this.lowRiskCount,
    required this.safeCount,
  });

  factory FireRiskStatistics.fromJson(Map<String, dynamic> json) {
    return FireRiskStatistics(
      totalPoints: (json['total_points'] as num?)?.toInt() ?? 0,
      riskDistribution: Map<String, int>.from(
        (json['risk_distribution'] as Map?)?.map(
              (k, v) => MapEntry(k.toString(), (v as num).toInt()),
            ) ??
            {},
      ),
      averageFireProbability:
          (json['average_fire_probability'] as num?)?.toDouble() ?? 0.0,
      averageCombinedRiskScore:
          (json['average_combined_risk_score'] as num?)?.toDouble() ?? 0.0,
      highRiskCount: (json['high_risk_count'] as num?)?.toInt() ?? 0,
      mediumRiskCount: (json['medium_risk_count'] as num?)?.toInt() ?? 0,
      lowRiskCount: (json['low_risk_count'] as num?)?.toInt() ?? 0,
      safeCount: (json['safe_count'] as num?)?.toInt() ?? 0,
    );
  }
}

/// API response for error handling
class ApiError {
  final String message;
  final int? statusCode;
  final dynamic originalError;

  ApiError({required this.message, this.statusCode, this.originalError});

  @override
  String toString() => 'ApiError: $message (Status: $statusCode)';
}

extension StringExt on String {
  T? let<T>(T Function(String) fn) {
    try {
      return fn(this);
    } catch (_) {
      return null;
    }
  }
}
