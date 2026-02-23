import 'package:latlong2/latlong.dart';

/// A single fire detection point from FIRMS.
class FirePoint {
  final LatLng position;
  final String? confidence;
  final double? frp;
  final double? brightness;
  final String? satellite;
  final String? instrument;
  final String? acqDate;
  final String? acqTime;

  FirePoint({
    required this.position,
    this.confidence,
    this.frp,
    this.brightness,
    this.satellite,
    this.instrument,
    this.acqDate,
    this.acqTime,
  });

  factory FirePoint.fromGeoJsonFeature(Map<String, dynamic> feature) {
    final coords = feature['geometry']['coordinates'] as List;
    final props = feature['properties'] as Map<String, dynamic>? ?? {};
    return FirePoint(
      position: LatLng(
        (coords[1] as num).toDouble(),
        (coords[0] as num).toDouble(),
      ),
      confidence: props['confidence']?.toString(),
      frp: (props['frp'] as num?)?.toDouble(),
      brightness:
          (props['brightness'] ??
                  props['bright_ti4'] ??
                  props['bright_ti5'] as num?)
              ?.toDouble(),
      satellite: props['satellite']?.toString(),
      instrument: props['instrument']?.toString(),
      acqDate: props['acq_date']?.toString(),
      acqTime: props['acq_time']?.toString(),
    );
  }
}

/// A fire risk point from ML prediction.
class FireRiskPoint {
  final LatLng position;
  final String riskClass;
  final double fireProbability;
  final double combinedRiskScore;

  FireRiskPoint({
    required this.position,
    required this.riskClass,
    required this.fireProbability,
    required this.combinedRiskScore,
  });

  factory FireRiskPoint.fromGeoJsonFeature(Map<String, dynamic> feature) {
    final coords = feature['geometry']['coordinates'] as List;
    final props = feature['properties'] as Map<String, dynamic>? ?? {};
    return FireRiskPoint(
      position: LatLng(
        (coords[1] as num).toDouble(),
        (coords[0] as num).toDouble(),
      ),
      riskClass: props['risk_class'] ?? 'SAFE_UNBURNABLE',
      fireProbability: (props['fire_probability'] as num?)?.toDouble() ?? 0.0,
      combinedRiskScore:
          (props['combined_risk_score'] as num?)?.toDouble() ?? 0.0,
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
}

/// Wind data at a point.
class WindData {
  final double speedMs;
  final double deg;
  final String source;

  WindData({required this.speedMs, required this.deg, required this.source});

  factory WindData.fromJson(Map<String, dynamic> json) {
    return WindData(
      speedMs: (json['speed_ms'] as num?)?.toDouble() ?? 0.0,
      deg: (json['deg'] as num?)?.toDouble() ?? 0.0,
      source: json['source']?.toString() ?? '',
    );
  }
}

/// A water feature (reservoir, source, tank, lake).
class WaterFeature {
  final LatLng position;
  final String name;
  final String type; // 'reservoir', 'source', 'tank', 'lake'
  final Map<String, dynamic> properties;

  WaterFeature({
    required this.position,
    required this.name,
    required this.type,
    this.properties = const {},
  });

  factory WaterFeature.fromGeoJsonFeature(
    Map<String, dynamic> feature,
    String type,
  ) {
    final geom = feature['geometry'] as Map<String, dynamic>;
    final props = feature['properties'] as Map<String, dynamic>? ?? {};

    double lat, lon;
    final geomType = geom['type'] as String;
    final coords = geom['coordinates'];

    if (geomType == 'Point') {
      lon = (coords[0] as num).toDouble();
      lat = (coords[1] as num).toDouble();
    } else if (geomType == 'Polygon') {
      final ring = coords[0] as List;
      lon =
          ring.fold<double>(0, (s, c) => s + (c[0] as num).toDouble()) /
          ring.length;
      lat =
          ring.fold<double>(0, (s, c) => s + (c[1] as num).toDouble()) /
          ring.length;
    } else if (geomType == 'MultiPolygon') {
      final ring = coords[0][0] as List;
      lon = (ring[0][0] as num).toDouble();
      lat = (ring[0][1] as num).toDouble();
    } else {
      lon = 27.14;
      lat = 38.42;
    }

    return WaterFeature(
      position: LatLng(lat, lon),
      name: props['name']?.toString() ?? type,
      type: type,
      properties: props,
    );
  }
}
