import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../config/app_theme.dart';
import '../models/fire_data.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../services/map_data_service.dart';
import '../widgets/map_control_panel.dart';
import 'login_screen.dart';

const int kFireSpreadMonitorIntervalMinutes = 15;
const double kFireSpreadStepDurationMinutes = 60.0;
const double kSecondsPerMinute = 60.0;

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  final MapController _mapCtrl = MapController();

  // Izmir boundary data synced with web behavior
  final List<List<List<LatLng>>> _izmirPolygons = [];
  final List<List<LatLng>> _izmirBoundaryLines = [];

  // Loading state
  bool _loading = false;
  String _statusText = '';

  // Map type
  bool _useSatellite = true;

  // Fire spread tracking
  List<Polygon> _spreadPolygons = [];
  LatLng? _spreadOrigin;
  dynamic _activeSpreadScenarioId;
  bool _isPickingSpreadLocation = false;
  WebSocketChannel? _spreadWsChannel;
  StreamSubscription? _spreadWsSub;
  String? _spreadAlertMsg;
  String? _spreadAlertSeverity;

  // New Spread UI states (Synced with Web)
  LatLng? _mySpreadLocation = const LatLng(38.4537, 27.2183); // Default mock
  Map<String, dynamic>? _lastSpreadData;
  double? _windDir;
  double? _windSpeedMs;
  double? _etaMin;
  double? _distKm;
  Map<String, dynamic>? _scenarioProps;
  Map<String, dynamic>? _scenarioWeather;
  double? _elapsedMinutes;
  List<dynamic>? _spreadScenariosCache;

  late ApiService _api;
  Map<String, String> _copy = {};

  @override
  void initState() {
    super.initState();
    _api = ApiService();
    // Set token if available
    final auth = context.read<AuthService>();
    if (auth.user?.accessToken != null) {
      _api.setToken(auth.user!.accessToken);
    }
    _loadWebSyncedCopy();
    _loadIzmirBoundary();

    // Initialize map data service
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final mapDataService = context.read<MapDataService>();
      mapDataService.loadRiskStatistics();
    });
  }

  Future<void> _loadIzmirBoundary() async {
    try {
      final gj = await _api.getIzmirBoundaryGeoJson();
      final polygons = <List<List<LatLng>>>[];
      final boundaryLines = <List<LatLng>>[];

      void addPolygonRings(List ringsRaw) {
        final rings = <List<LatLng>>[];
        for (final ringRaw in ringsRaw) {
          if (ringRaw is! List || ringRaw.isEmpty) continue;
          final ring = <LatLng>[];
          for (final c in ringRaw) {
            if (c is! List || c.length < 2) continue;
            ring.add(
              LatLng((c[1] as num).toDouble(), (c[0] as num).toDouble()),
            );
          }
          if (ring.isNotEmpty) {
            rings.add(ring);
          }
        }

        if (rings.isNotEmpty) {
          polygons.add(rings);
          boundaryLines.add(rings.first);
        }
      }

      void extractGeometry(Map<String, dynamic>? geom) {
        if (geom == null) return;
        final type = geom['type'];
        final coords = geom['coordinates'];
        if (type == 'Polygon' && coords is List) {
          addPolygonRings(coords);
          return;
        }
        if (type == 'MultiPolygon' && coords is List) {
          for (final poly in coords) {
            if (poly is List) addPolygonRings(poly);
          }
        }
      }

      if (gj['type'] == 'FeatureCollection' && gj['features'] is List) {
        for (final feat in (gj['features'] as List)) {
          if (feat is Map<String, dynamic>) {
            extractGeometry(feat['geometry'] as Map<String, dynamic>?);
          }
        }
      } else if (gj['type'] == 'Feature') {
        extractGeometry(gj['geometry'] as Map<String, dynamic>?);
      } else {
        extractGeometry(gj);
      }

      if (!mounted) return;
      setState(() {
        _izmirPolygons
          ..clear()
          ..addAll(polygons);
        _izmirBoundaryLines
          ..clear()
          ..addAll(boundaryLines);
      });
    } catch (_) {
      // Keep behavior aligned with web: if boundary can't load, do not clip.
    }
  }

  bool _isPointInRing(double lat, double lon, List<LatLng> ring) {
    if (ring.length < 3) return false;
    var inside = false;
    for (var i = 0; i < ring.length; i++) {
      final p1 = ring[i];
      final p2 = ring[(i + 1) % ring.length];
      final y1 = p1.latitude;
      final y2 = p2.latitude;
      final x1 = p1.longitude;
      final x2 = p2.longitude;

      final intersects = (y1 > lat) != (y2 > lat);
      if (!intersects) continue;

      final xAtLat = (x2 - x1) * (lat - y1) / (y2 - y1) + x1;
      if (lon < xAtLat) inside = !inside;
    }
    return inside;
  }

  bool _isInIzmir(double lat, double lon) {
    if (_izmirPolygons.isEmpty) return true;

    for (final polygonRings in _izmirPolygons) {
      if (polygonRings.isEmpty) continue;
      final outer = polygonRings.first;
      final holes = polygonRings.skip(1);

      if (_isPointInRing(lat, lon, outer)) {
        var inHole = false;
        for (final hole in holes) {
          if (_isPointInRing(lat, lon, hole)) {
            inHole = true;
            break;
          }
        }
        if (!inHole) return true;
      }
    }
    return false;
  }

  LatLng? _featureRepresentativePoint(Map<String, dynamic> feature) {
    final geom = feature['geometry'];
    if (geom is! Map<String, dynamic>) return null;
    final type = geom['type'];
    final coords = geom['coordinates'];

    try {
      if (type == 'Point' && coords is List && coords.length >= 2) {
        return LatLng(
          (coords[1] as num).toDouble(),
          (coords[0] as num).toDouble(),
        );
      }
      if (type == 'Polygon' && coords is List && coords.isNotEmpty) {
        final first = coords[0][0] as List;
        return LatLng(
          (first[1] as num).toDouble(),
          (first[0] as num).toDouble(),
        );
      }
      if (type == 'MultiPolygon' && coords is List && coords.isNotEmpty) {
        final first = coords[0][0][0] as List;
        return LatLng(
          (first[1] as num).toDouble(),
          (first[0] as num).toDouble(),
        );
      }
      if (type == 'LineString' && coords is List && coords.isNotEmpty) {
        final first = coords[0] as List;
        return LatLng(
          (first[1] as num).toDouble(),
          (first[0] as num).toDouble(),
        );
      }
    } catch (_) {
      return null;
    }
    return null;
  }

  bool _isFeatureInIzmir(Map<String, dynamic> feature) {
    final p = _featureRepresentativePoint(feature);
    if (p == null) return false;
    return _isInIzmir(p.latitude, p.longitude);
  }

  Future<void> _loadDefaultPublicLayers() async {
    if (_loading) return;
    // Water layers removed per user request
  }

  Future<void> _loadWebSyncedCopy() async {
    try {
      final data = await _api.getMapUiCopy();
      if (!mounted) return;
      setState(() {
        _copy = data.map((k, v) => MapEntry(k, v?.toString() ?? ''));
      });
    } catch (_) {
      // Keep built-in defaults when backend copy endpoint is unreachable.
    }
  }

  String _t(String key, String fallback) {
    final value = _copy[key];
    if (value == null || value.trim().isEmpty) return fallback;
    return value;
  }

  @override
  void dispose() {
    _spreadWsSub?.cancel();
    _spreadWsChannel?.sink.close();
    _mapCtrl.dispose();
    super.dispose();
  }

  void _setStatus(String msg) {
    if (mounted) setState(() => _statusText = msg);
  }

  bool _isTransientSpreadStatus(String status) {
    final lower = status.toLowerCase();
    return lower.contains('yangın yayılımı canlı izleniyor') ||
        lower.contains('canlı veriler bağlanıyor') ||
        lower.contains('senaryo oluşturuluyor') ||
        lower.contains('haritadan yangın başlangıç noktası seçin');
  }

  // ─── Fire Spread ──────────────────────────────────────────────────────────

  void _connectSpreadWS(dynamic scenarioId) {
    _spreadWsSub?.cancel();
    _spreadWsChannel?.sink.close();

    final wsUrl = _api.getSpreadWsUrl(scenarioId);
    try {
      _spreadWsChannel = WebSocketChannel.connect(Uri.parse(wsUrl));
      _spreadWsSub = _spreadWsChannel!.stream.listen(
        (raw) {
          final data = jsonDecode(raw as String) as Map<String, dynamic>;
          if (data['event'] == 'spread_update') {
            _onSpreadUpdate(data);
          } else if (data['event'] == 'heartbeat') {
            _spreadWsChannel?.sink.add('ping');
          }
        },
        onDone: () {
          if (_activeSpreadScenarioId == scenarioId && mounted) {
            Future.delayed(const Duration(seconds: 8), () {
              if (_activeSpreadScenarioId == scenarioId)
                _connectSpreadWS(scenarioId);
            });
          }
        },
        onError: (_) {},
        cancelOnError: false,
      );
    } catch (_) {}
  }

  void _onSpreadUpdate(Map<String, dynamic> data) {
    if (!mounted) return;

    final feature = data['spread_polygon'] as Map<String, dynamic>?;
    final origin = data['origin'] as Map<String, dynamic>?;
    final alerts = data['alerts'] as List<dynamic>? ?? [];
    final weather = data['weather'] as Map<String, dynamic>?;
    final elapsed = data['elapsed_minutes'] != null
        ? double.tryParse(data['elapsed_minutes'].toString())
        : null;

    List<Polygon> polys = [];
    if (feature != null) {
      // Support both Feature and direct Geometry types
      final Map<String, dynamic>? geometry = (feature['type'] == 'Feature')
          ? feature['geometry'] as Map<String, dynamic>?
          : feature;

      final props = (feature['type'] == 'Feature')
          ? feature['properties'] as Map<String, dynamic>?
          : null;

      final coordsRaw = (geometry?['coordinates']?[0] as List?) ?? [];
      final coords = coordsRaw.map((c) {
        final clist = c as List;
        return LatLng(
          double.tryParse(clist[1].toString()) ?? 0.0,
          double.tryParse(clist[0].toString()) ?? 0.0,
        );
      }).toList();

      if (coords.isNotEmpty) {
        polys = [
          Polygon(
            points: coords,
            color: const Color(0x50FF4500),
            borderColor: const Color(0xFFFF4500),
            borderStrokeWidth: 2.5,
          ),
        ];
      }
      _scenarioProps = props; // Update properties for the info panel
    }

    String? alertMsg;
    String? alertSev;
    if (alerts.isNotEmpty) {
      final worst = alerts.reduce((a, b) {
        const rank = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3};
        return (rank[a['severity']] ?? 4) <= (rank[b['severity']] ?? 4) ? a : b;
      });
      alertMsg = worst['message'] as String?;
      alertSev = worst['severity'] as String?;
    }

    setState(() {
      _spreadPolygons = polys;
      _spreadOrigin = origin != null
          ? LatLng(
              double.tryParse(origin['lat']?.toString() ?? '0') ?? 0.0,
              double.tryParse(origin['lon']?.toString() ?? '0') ?? 0.0,
            )
          : null;
      _scenarioWeather = weather;
      _elapsedMinutes = elapsed;
      // _scenarioProps updated above in feature block

      _windDir = weather != null
          ? double.tryParse(weather['wind_dir_deg']?.toString() ?? '')
          : null;
      _windSpeedMs = weather != null
          ? double.tryParse(weather['wind_speed_ms']?.toString() ?? '')
          : null;

      if (alertMsg != null) {
        _spreadAlertMsg = alertMsg;
        _spreadAlertSeverity = alertSev;
      }

      // Calculate ETA if user location is set
      if (_mySpreadLocation != null &&
          _spreadOrigin != null &&
          weather != null) {
        final res = _calculateEta(data);
        if (res != null) {
          _etaMin = res['eta'];
          _distKm = res['distKm'];
        }
      }
    });
  }

  Map<String, double?>? _calculateEta(Map<String, dynamic> data) {
    final origin = data['origin'];
    if (origin == null || _mySpreadLocation == null) return null;

    final originLat = double.tryParse(origin['lat']?.toString() ?? '') ?? 0.0;
    final originLon = double.tryParse(origin['lon']?.toString() ?? '') ?? 0.0;
    final userLat = _mySpreadLocation!.latitude;
    final userLon = _mySpreadLocation!.longitude;

    // Haversine
    const r = 6371.0;
    double toRad(double deg) => deg * pi / 180;
    final dLat = toRad(userLat - originLat);
    final dLon = toRad(userLon - originLon);
    final a =
        sin(dLat / 2) * sin(dLat / 2) +
        cos(toRad(originLat)) *
            cos(toRad(userLat)) *
            sin(dLon / 2) *
            sin(dLon / 2);
    final distKm = 2 * r * atan2(sqrt(a), sqrt(1 - a));
    final distM = distKm * 1000;

    final weather = data['weather'] as Map<String, dynamic>?;
    if (weather == null) return {'eta': null, 'distKm': distKm};

    final wDir =
        double.tryParse(weather['wind_dir_deg']?.toString() ?? '') ?? 240.0;
    final wSpd =
        double.tryParse(weather['wind_speed_ms']?.toString() ?? '') ?? 6.0;
    final hum = double.tryParse(weather['humidity']?.toString() ?? '') ?? 50.0;
    final temp =
        double.tryParse(weather['temperature_c']?.toString() ?? '') ?? 25.0;

    // Bearing
    final dx = sin(toRad(userLon - originLon)) * cos(toRad(userLat));
    final dy =
        cos(toRad(originLat)) * sin(toRad(userLat)) -
        sin(toRad(originLat)) *
            cos(toRad(userLat)) *
            cos(toRad(userLon - originLon));
    final bearing = (atan2(dx, dy) * 180 / pi + 360) % 360;
    final angleDiff = (bearing - wDir + 180).abs() % 360 - 180;
    final angleDiffAbs = angleDiff.abs();

    // Spread Rate (Sync with fire_spread_engine.py)
    const base = 0.15;
    final wf = 1.0 + wSpd * 0.22;
    final hf = (100 - hum.clamp(0, 100)) / 100.0;
    final tf = 1.0 + (temp - 20).clamp(0, 50) * 0.015;
    final rateMs = base * wf * hf * tf;

    final cosF = cos(angleDiffAbs * pi / 180);
    final dirR = cosF >= 0
        ? rateMs * (cosF * 0.88 + 0.12)
        : rateMs * (cosF.abs() * 0.04 + 0.08);

    final elapsed =
        double.tryParse(data['elapsed_minutes']?.toString() ?? '') ?? 0.0;
    final reach = dirR * elapsed * kSecondsPerMinute;

    if (distM <= reach) return {'eta': 0.0, 'distKm': distKm};
    if (dirR < 1e-6) return {'eta': null, 'distKm': distKm};

    return {
      'eta': (distM - reach) / dirR / kSecondsPerMinute,
      'distKm': distKm,
    };
  }

  void _stopSpreadTracking() {
    _spreadWsSub?.cancel();
    _spreadWsChannel?.sink.close();
    _spreadWsChannel = null;
    _spreadWsSub = null;
    if (mounted) {
      setState(() {
        _activeSpreadScenarioId = null;
        _spreadPolygons = [];
        _spreadOrigin = null;
        _spreadAlertMsg = null;
        _spreadAlertSeverity = null;
        _scenarioProps = null;
        _scenarioWeather = null;
        _elapsedMinutes = null;
        _etaMin = null;
        _distKm = null;
        _statusText = '';
        _isPickingSpreadLocation = false;
      });
    }
  }

  Future<void> _startCustomSpreadSimulation(LatLng latLng) async {
    setState(() {
      _isPickingSpreadLocation = false;
      _loading = true;
      _spreadOrigin = latLng;
      _spreadPolygons = [];
      _activeSpreadScenarioId = null;
      _spreadAlertMsg = null;
      _lastSpreadData = null;
      _etaMin = null;
      _distKm = null;
      _setStatus('Senaryo oluşturuluyor...');
    });

    try {
      final now = DateTime.now().toLocal();
      final timeStr =
          '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';

      final res = await _api.createSpreadScenario(
        name: 'Mobil Simülasyon $timeStr',
        lat: latLng.latitude,
        lon: latLng.longitude,
      );

      final newId = res['id'];
      if (newId == null)
        throw Exception('Sunucudan geçerli bir senaryo ID alınamadı.');

      setState(() {
        _activeSpreadScenarioId = newId;
        _setStatus('Canlı veriler bağlanıyor...');
      });
      _spreadScenariosCache = null;

      _connectSpreadWS(newId);
      _setStatus('Yangın yayılımı canlı izleniyor...');
    } catch (e) {
      _setStatus('Hata: ${e.toString().replaceAll('Exception:', '').trim()}');
      setState(() {
        _spreadOrigin = null;
        _loading = false;
      });
      // Auto-clear error status after 5 seconds
      Future.delayed(const Duration(seconds: 5), () {
        if (mounted && _statusText.contains('Hata:')) {
          setState(() => _statusText = '');
        }
      });
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _loadSpreadScenarios() async {
    setState(() => _loading = true);
    try {
      final list = _spreadScenariosCache ?? await _api.getSpreadScenarios();
      if (_spreadScenariosCache == null) {
        _spreadScenariosCache = list;
      }
      if (!mounted) return;
      _showSpreadListModal(list);
    } catch (e) {
      _setStatus('Senaryolar yüklenemedi: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  void _showSpreadListModal(List<dynamic> scenarios) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        height: MediaQuery.of(context).size.height * 0.45,
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.98),
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.1),
              blurRadius: 20,
              spreadRadius: 5,
            )
          ],
        ),
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Yangın Senaryoları',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextButton.icon(
                      onPressed: scenarios.isEmpty
                          ? null
                          : () async {
                              final confirm = await showDialog<bool>(
                                context: context,
                                builder: (dialogCtx) => AlertDialog(
                                  title: const Text(
                                    'Tüm senaryolar silinsin mi?',
                                  ),
                                  content: const Text(
                                    'Bu işlem tüm yangın yayılım senaryolarını ve snapshot kayıtlarını siler.',
                                  ),
                                  actions: [
                                    TextButton(
                                      onPressed: () =>
                                          Navigator.pop(dialogCtx, false),
                                      child: const Text('Vazgeç'),
                                    ),
                                    FilledButton(
                                      onPressed: () =>
                                          Navigator.pop(dialogCtx, true),
                                      child: const Text('Sil'),
                                    ),
                                  ],
                                ),
                              );

                              if (confirm != true) return;
                              if (_activeSpreadScenarioId != null) {
                                _stopSpreadTracking();
                              }
                              await _api.deleteAllSpreadScenarios();
                              _spreadScenariosCache = null;
                              if (ctx.mounted) Navigator.pop(ctx);
                              await _loadSpreadScenarios();
                            },
                      icon: const Icon(Icons.delete_outline),
                      label: const Text('Tümünü Sil'),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.pop(ctx),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 10),
            Expanded(
              child: scenarios.isEmpty
                  ? const Center(child: Text('Henüz senaryo yok.'))
                  : ListView.separated(
                      itemCount: scenarios.length,
                      separatorBuilder: (_, __) => const Divider(),
                      itemBuilder: (context, index) {
                        final s = scenarios[index];
                        final id = s['id'];
                        final name = s['name'] ?? 'İsimsiz Senaryo';
                        final active = s['status'] == 'active';
                        final isTracking = _activeSpreadScenarioId == id;

                        return ListTile(
                          title: Text(
                            name,
                            style: TextStyle(
                              fontWeight: active
                                  ? FontWeight.bold
                                  : FontWeight.normal,
                              color: active
                                  ? Colors.orange[800]
                                  : Colors.grey[700],
                            ),
                          ),
                          subtitle: Text(
                            'ID: $id • ${double.tryParse(s['elapsed_minutes']?.toString() ?? '0')?.toStringAsFixed(0) ?? '0'} dk • ${double.tryParse(s['origin_lat']?.toString() ?? '0')?.toStringAsFixed(3)}, ${double.tryParse(s['origin_lon']?.toString() ?? '0')?.toStringAsFixed(3)}',
                            style: const TextStyle(fontSize: 12),
                          ),
                          trailing: TextButton(
                            onPressed: () {
                              Navigator.pop(ctx);
                              if (isTracking) {
                                _stopSpreadTracking();
                              } else {
                                _activeSpreadScenarioId = id;
                                _connectSpreadWS(id);
                              }
                            },
                            child: Text(isTracking ? 'Durdur' : 'Takip Et'),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  // ─── Reset ────────────────────────────────────────────

  void _resetMap() {
    setState(() {
      _statusText = _t('status_map_reset', 'Harita sıfırlandı');
    });
    _mapCtrl.move(const LatLng(38.42, 27.14), 8);
  }

  // ─── Build ────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final username = auth.user?.username ?? 'Kullanıcı';
    final userRole = auth.user?.role ?? 'user';
    final roleLabel = userRole == 'firefighter' ? 'İtfaiyeci' : 'Kullanıcı';

    return Scaffold(
      body: Stack(
        children: [
          // Map
          FlutterMap(
            mapController: _mapCtrl,
            options: MapOptions(
              initialCenter: const LatLng(38.42, 27.14),
              initialZoom: 8,
              maxZoom: 19,
              onTap: (tapPosition, latLng) {
                if (_isPickingSpreadLocation) {
                  _startCustomSpreadSimulation(latLng);
                }
              },
            ),
            children: [
              // Tile layer
              TileLayer(
                urlTemplate: _useSatellite
                    ? 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
                    : 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                maxZoom: 19,
                userAgentPackageName: 'com.koru.app',
              ),

              // Izmir boundary line overlay (drawn above data layers)
              if (_izmirBoundaryLines.isNotEmpty)
                PolylineLayer(
                  polylines: _izmirBoundaryLines
                      .map(
                        (line) => Polyline(
                          points: line,
                          color: const Color(0xFF8B0000),
                          strokeWidth: 3,
                        ),
                      )
                      .toList(),
                ),

              // Home Link (Line between fire and home)
              if (_spreadOrigin != null && _mySpreadLocation != null)
                PolylineLayer(
                  polylines: <Polyline>[
                    Polyline(
                      points: [_spreadOrigin!, _mySpreadLocation!],
                      color: _etaMin == 0
                          ? Colors.red
                          : (_etaMin != null && _etaMin! <= 90
                                ? Colors.orange
                                : Colors.blue.withValues(alpha: 0.6)),
                      strokeWidth: 3,
                    ),
                  ],
                ),

              // Fire spread polygon (live tracking)
              if (_spreadPolygons.isNotEmpty)
                PolygonLayer(polygons: _spreadPolygons),

              // Fire spread origin and Wind Arrow
              if (_spreadOrigin != null) ...[
                CircleLayer(
                  circles: [
                    CircleMarker(
                      point: _spreadOrigin!,
                      radius: 12,
                      color: const Color(0xCCFF4500),
                      borderColor: Colors.red,
                      borderStrokeWidth: 3,
                    ),
                  ],
                ),
                if (_windDir != null)
                  MarkerLayer(
                    markers: [
                      Marker(
                        point: _spreadOrigin!,
                        width: 60,
                        height: 60,
                        child: Transform.rotate(
                          angle: (_windDir! + 180) * pi / 180,
                          child: const Icon(
                            Icons.arrow_upward,
                            color: Colors.orange,
                            size: 40,
                          ),
                        ),
                      ),
                    ],
                  ),
              ],

              // Home Marker
              if (_mySpreadLocation != null)
                MarkerLayer(
                  markers: [
                    Marker(
                      point: _mySpreadLocation!,
                      width: 40,
                      height: 40,
                      child: Icon(
                        Icons.home,
                        color: _etaMin == 0
                            ? Colors.red
                            : (_etaMin != null && _etaMin! <= 90
                                  ? Colors.orange
                                  : Colors.blue),
                        size: 30,
                      ),
                    ),
                  ],
                ),
            ],
          ),

          // Fire spread alert banner
          if (_spreadAlertMsg != null)
            Positioned(
              top: 12,
              left: 16,
              right: 16,
              child: GestureDetector(
                onTap: () => setState(() => _spreadAlertMsg = null),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    color: _spreadAlertSeverity == 'critical'
                        ? const Color(0xEEb71c1c)
                        : _spreadAlertSeverity == 'high'
                        ? const Color(0xEEe65100)
                        : const Color(0xEE1a1a1a),
                    borderRadius: BorderRadius.circular(12),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.4),
                        blurRadius: 10,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Row(
                    children: [
                      Icon(
                        _spreadAlertSeverity == 'critical'
                            ? Icons.warning_amber_rounded
                            : Icons.info_outline,
                        color: Colors.white,
                        size: 20,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          _spreadAlertMsg!,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      const Icon(Icons.close, color: Colors.white60, size: 16),
                    ],
                  ),
                ),
              ),
            ),

          // Detailed Info Panel (Bottom Left)
          if (_activeSpreadScenarioId != null)
            Positioned(bottom: 120, left: 16, child: _buildSpreadInfoPanel()),

          // ETA Box (Top Center - below alert)
          if (_activeSpreadScenarioId != null &&
              (_etaMin != null || _distKm != null))
            Positioned(
              top: _spreadAlertMsg != null ? 70 : 12,
              left: 16,
              right: 16,
              child: Center(child: _buildEtaBox()),
            ),

          // Loading overlay
          if (_loading)
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              child: const LinearProgressIndicator(
                backgroundColor: Colors.transparent,
                color: AppTheme.brandRed,
              ),
            ),

          // Status bar
          if (_statusText.isNotEmpty &&
              (_activeSpreadScenarioId != null ||
                  _isPickingSpreadLocation ||
                  !_isTransientSpreadStatus(_statusText)))
            Positioned(
              top: 8,
              left: 60,
              right: 60,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 10,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xEE1a1a1a),
                  borderRadius: BorderRadius.circular(25),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.3),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.max,
                  children: [
                    const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(
                          Colors.orange,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        _statusText,
                        textAlign: TextAlign.center,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                          letterSpacing: 0.3,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),

          // Map type toggle and Control panel overlapping the map directly
          Positioned(
            top: MediaQuery.of(context).padding.top + 12,
            right: 12,
            child: Column(
              children: [
                _circularMapBtn(
                  icon: Icons.layers_rounded,
                  onTap: _loadAndShowControlPanel,
                ),
                const SizedBox(height: 12),
                _circularMapBtn(
                  icon: _useSatellite ? Icons.map_rounded : Icons.satellite_alt_rounded,
                  onTap: () => setState(() => _useSatellite = !_useSatellite),
                ),
              ],
            ),
          ),

          // Logout / Back to Login button
          Positioned(
            top: MediaQuery.of(context).padding.top + 12,
            left: 12,
            child: _circularMapBtn(
              icon: Icons.logout_rounded,
              color: Colors.redAccent,
              onTap: () async {
                await context.read<AuthService>().logout();
                if (context.mounted) {
                  Navigator.pushReplacement(
                    context,
                    MaterialPageRoute(builder: (_) => const LoginScreen()),
                  );
                }
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _contactItem(String label, String value) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '$label ',
          style: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w800,
            color: AppTheme.brandRed,
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            color: AppTheme.brandRed,
          ),
        ),
      ],
    );
  }

  // ─── Build map layers ─────────────────────────────────

  // ─── Control panel bottom sheet ───────────────────────

  Future<void> _loadAndShowControlPanel() async {
    setState(() => _loading = true);
    try {
      _spreadScenariosCache = await _api.getSpreadScenarios();
      if (!mounted) return;
      _showControlPanel();
    } catch (e) {
      _setStatus('Veriler yüklenemedi: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  void _showControlPanel() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => MapControlPanel(
        hasActiveSpread: _activeSpreadScenarioId != null,
        onShowSpreadScenario: () {
          Navigator.pop(ctx);
          if (_activeSpreadScenarioId != null) {
            _stopSpreadTracking();
          }
          setState(() {
            _isPickingSpreadLocation = true;
            _setStatus('Lütfen haritadan bir yer seçin');
          });
        },
        onShowSpreadList: () {}, // Handled inline now
        scenarios: _spreadScenariosCache ?? [],
        activeScenarioId: _activeSpreadScenarioId,
        onToggleTracking: (id, isTracking) {
          if (isTracking) {
            _stopSpreadTracking();
          } else {
            setState(() {
              _activeSpreadScenarioId = id;
            });
            _connectSpreadWS(id);
          }
          // Refresh panel state
          (ctx as Element).markNeedsBuild();
        },
        onDeleteAll: () async {
          final confirm = await showDialog<bool>(
            context: context,
            builder: (dialogCtx) => AlertDialog(
              title: const Text('Tüm senaryolar silinsin mi?'),
              content: const Text('Bu işlem tüm kayıtları siler.'),
              actions: [
                TextButton(onPressed: () => Navigator.pop(dialogCtx, false), child: const Text('Vazgeç')),
                FilledButton(onPressed: () => Navigator.pop(dialogCtx, true), child: const Text('Sil')),
              ],
            ),
          );
          if (confirm == true) {
            if (_activeSpreadScenarioId != null) _stopSpreadTracking();
            await _api.deleteAllSpreadScenarios();
            _spreadScenariosCache = null;
            Navigator.pop(ctx);
            _showControlPanel(); // Re-open to refresh
          }
        },
        tr: _t,
      ),
    );
  }

  // ─── Drawer (sidebar) ────────────────────────────────

  Widget _buildDrawer(BuildContext context) {
    return Drawer(
      backgroundColor: AppTheme.darkGreen,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 20),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 18),
              child: Text(
                'KORU',
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w800,
                  color: Colors.white,
                  letterSpacing: 2,
                ),
              ),
            ),
            const SizedBox(height: 24),
            _drawerItem(
              icon: Icons.contact_mail,
              label: _t('menu_contact', 'Bize Ulaşın'),
              onTap: () {
                Navigator.pop(context);
                launchUrl(
                  Uri.parse('https://www.izmir.bel.tr/'),
                  mode: LaunchMode.externalApplication,
                );
              },
            ),
            const Spacer(),
            Padding(
              padding: const EdgeInsets.all(18),
              child: Text(
                _t('header_title', 'KORU Yangın Önleme Platformu'),
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.5),
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _drawerItem({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return ListTile(
      leading: Icon(icon, color: Colors.white, size: 22),
      title: Text(
        label,
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w600,
          fontSize: 14,
          letterSpacing: 0.2,
        ),
      ),
      onTap: onTap,
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 4),
      shape: Border(
        bottom: BorderSide(color: Colors.white.withValues(alpha: 0.12)),
      ),
    );
  }

  Widget _buildSpreadInfoPanel() {
    final windKmh = (_windSpeedMs != null ? (_windSpeedMs! * 3.6) : 0.0)
        .toStringAsFixed(1);
    final spreadRateKmh =
        (_scenarioProps?['spread_rate_ms'] != null
                ? (double.tryParse(
                        _scenarioProps!['spread_rate_ms'].toString(),
                      )! *
                      3.6)
                : 0.0)
            .toStringAsFixed(2);
    final frontDist = _scenarioProps?['front_radius_km'] != null
        ? double.tryParse(
                _scenarioProps!['front_radius_km'].toString(),
              )?.toStringAsFixed(2) ??
              '-'
        : '-';
    final humidity = _scenarioWeather?['humidity'] != null
        ? double.tryParse(
                _scenarioWeather!['humidity'].toString(),
              )?.toStringAsFixed(0) ??
              '-'
        : '-';
    final temp = _scenarioWeather?['temperature_c'] != null
        ? double.tryParse(
                _scenarioWeather!['temperature_c'].toString(),
              )?.toStringAsFixed(1) ??
              '-'
        : '-';

    return Container(
      width: 220,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xEE1a1a1a),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.orange.withValues(alpha: 0.3)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.5),
            blurRadius: 12,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            'YANGIN SİMÜLASYONU',
            style: TextStyle(
              color: Colors.orange,
              fontSize: 11,
              fontWeight: FontWeight.w900,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 8),
          _buildInfoRow(
            'Süre:',
            '${(double.tryParse((_elapsedMinutes ?? 0).toString()) ?? 0.0).toStringAsFixed(0)} dk',
          ),
          _buildInfoRow(
            'Kural:',
            '$kFireSpreadMonitorIntervalMinutes dk / ${kFireSpreadStepDurationMinutes.toStringAsFixed(0)} dk',
          ),
          _buildInfoRow('Ön Cephe:', '$frontDist km'),
          _buildInfoRow('Yayılım Hızı:', '$spreadRateKmh km/sa'),
          const Divider(color: Colors.white10, height: 16),
          const Text(
            'CANLI HAVA DURUMU',
            style: TextStyle(
              color: Colors.white54,
              fontSize: 9,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          _buildInfoRow(
            'Rüzgar:',
            '$windKmh km/sa  ${_windDir?.toStringAsFixed(0) ?? '-'}°',
          ),
          _buildInfoRow('Sıcaklık:', '$temp°C'),
          _buildInfoRow('Nem:', '%$humidity'),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(color: Colors.white70, fontSize: 11),
          ),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEtaBox() {
    String msg;
    Color color;

    if (_etaMin == 0) {
      msg = 'TEHLİKE: Yangın ev noktasına ulaştı!';
      color = const Color(0xFFb71c1c);
    } else if (_etaMin != null && _etaMin! <= 90) {
      msg = 'Yüksek Risk: ETA ${_etaMin!.toStringAsFixed(0)} dk';
      color = Colors.red;
    } else if (_etaMin != null && _etaMin! <= 240) {
      msg = 'İzleme: ETA ${_etaMin!.toStringAsFixed(0)} dk';
      color = Colors.orange;
    } else {
      msg = 'Güvenli: Mesafe ${_distKm?.toStringAsFixed(1) ?? '-'} km';
      color = Colors.green;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Text(
        msg,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  Widget _circularMapBtn({required IconData icon, required VoidCallback onTap, Color? color}) {
    return Material(
      color: AppTheme.webBg.withValues(alpha: 0.85),
      borderRadius: BorderRadius.circular(30),
      elevation: 8,
      child: InkWell(
        borderRadius: BorderRadius.circular(30),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: AppTheme.webAccent.withValues(alpha: 0.3), width: 1.5),
          ),
          child: Icon(
            icon,
            size: 22,
            color: color ?? AppTheme.webAccent,
          ),
        ),
      ),
    );
  }
}
