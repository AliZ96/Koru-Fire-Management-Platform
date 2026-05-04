import 'dart:async';
import 'dart:convert';
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

  // Layer data
  List<WaterFeature> _reservoirs = [];
  List<WaterFeature> _waterSources = [];
  List<WaterFeature> _waterTanks = [];
  List<WaterFeature> _lakes = [];
  List<Polygon> _lakePolygons = [];
  WindData? _windData; // ignore: unused_field – reserved for wind overlay

  // Layer visibility toggles
  bool _showReservoirs = false;
  bool _showWaterSources = false;
  bool _showWaterTanks = false;
  bool _showLakes = false;

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
    await _toggleReservoirs();
    await _toggleWaterSources();
    await _toggleLakes();
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

  // ─── Fire Spread ──────────────────────────────────────────────────────────

  void _connectSpreadWS(int scenarioId) {
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

    List<Polygon> polys = [];
    if (feature != null) {
      final coords =
          (feature['geometry']?['coordinates']?[0] as List?)
              ?.map(
                (c) =>
                    LatLng((c[1] as num).toDouble(), (c[0] as num).toDouble()),
              )
              .toList() ??
          [];
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
              (origin['lat'] as num).toDouble(),
              (origin['lon'] as num).toDouble(),
            )
          : null;
      if (alertMsg != null) {
        _spreadAlertMsg = alertMsg;
        _spreadAlertSeverity = alertSev;
      }
    });
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
      });
    }
  }

  Future<void> _startCustomSpreadSimulation(LatLng latLng) async {
    setState(() {
      _isPickingSpreadLocation = false;
      _loading = true;
      _setStatus('Simülasyon oluşturuluyor...');
    });
    try {
      final now = DateTime.now().toLocal();
      final timeStr = '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
      final res = await _api.createSpreadScenario(
        name: 'Mobil Simülasyon $timeStr',
        lat: latLng.latitude,
        lon: latLng.longitude,
      );
      final newId = res['id'];
      setState(() {
        _activeSpreadScenarioId = newId;
      });
      _connectSpreadWS(newId);
      _setStatus('Yangın yayılımı hesaplanıyor...');
    } catch (e) {
      _setStatus('Simülasyon hatası: $e');
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _loadSpreadScenarios() async {
    setState(() => _loading = true);
    try {
      final list = await _api.getSpreadScenarios();
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
        height: MediaQuery.of(context).size.height * 0.7,
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
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
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.pop(ctx),
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
                              fontWeight: active ? FontWeight.bold : FontWeight.normal,
                              color: active ? Colors.orange[800] : Colors.grey[700],
                            ),
                          ),
                          subtitle: Text(
                            'ID: $id • ${s['elapsed_minutes']?.toStringAsFixed(0) ?? '0'} dk • ${s['origin_lat']?.toStringAsFixed(3)}, ${s['origin_lon']?.toStringAsFixed(3)}',
                            style: const TextStyle(fontSize: 12),
                          ),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              TextButton(
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
                              if (active)
                                IconButton(
                                  icon: const Icon(Icons.stop_circle_outlined, color: Colors.red),
                                  onPressed: () async {
                                    await _api.stopSpreadScenario(id);
                                    Navigator.pop(ctx);
                                    _loadSpreadScenarios();
                                  },
                                ),
                            ],
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

  // ─── Water layers ─────────────────────────────────────

  Future<void> _toggleReservoirs() async {
    if (_showReservoirs) {
      setState(() {
        _showReservoirs = false;
        _reservoirs = [];
      });
      _setStatus('Su Rezervuarları kapatıldı');
      return;
    }
    setState(() => _loading = true);
    _setStatus('Su Rezervuarları yükleniyor...');
    try {
      final gj = await _api.getDams();
      final features = (gj['features'] as List?) ?? [];
      final items = features
          .map(
            (f) => WaterFeature.fromGeoJsonFeature(
              f as Map<String, dynamic>,
              'reservoir',
            ),
          )
          .where((w) => _isInIzmir(w.position.latitude, w.position.longitude))
          .toList();
      setState(() {
        _reservoirs = items;
        _showReservoirs = true;
      });
      _setStatus('Su Rezervuarları: ${items.length}');
    } catch (e) {
      _setStatus('Su Rezervuarları hatası: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _toggleWaterSources() async {
    if (_showWaterSources) {
      setState(() {
        _showWaterSources = false;
        _waterSources = [];
      });
      _setStatus('Su Kaynakları kapatıldı');
      return;
    }
    setState(() => _loading = true);
    _setStatus('Su Kaynakları yükleniyor...');
    try {
      final gj = await _api.getWaterSources();
      final features = (gj['features'] as List?) ?? [];
      final items = features
          .map(
            (f) => WaterFeature.fromGeoJsonFeature(
              f as Map<String, dynamic>,
              'source',
            ),
          )
          .where((w) => _isInIzmir(w.position.latitude, w.position.longitude))
          .toList();
      setState(() {
        _waterSources = items;
        _showWaterSources = true;
      });
      _setStatus('Su Kaynakları: ${items.length}');
    } catch (e) {
      _setStatus('Su Kaynakları hatası: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _toggleWaterTanks() async {
    if (_showWaterTanks) {
      setState(() {
        _showWaterTanks = false;
        _waterTanks = [];
      });
      _setStatus('Su tankları kapatıldı');
      return;
    }
    setState(() => _loading = true);
    _setStatus('Su tankları yükleniyor...');
    try {
      final gj = await _api.getWaterTanks();
      final features = (gj['features'] as List?) ?? [];
      final items = features
          .map(
            (f) => WaterFeature.fromGeoJsonFeature(
              f as Map<String, dynamic>,
              'tank',
            ),
          )
          .where((w) => _isInIzmir(w.position.latitude, w.position.longitude))
          .toList();
      setState(() {
        _waterTanks = items;
        _showWaterTanks = true;
      });
      _setStatus('Su tankları: ${items.length}');
    } catch (e) {
      _setStatus('Su tankları hatası: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _toggleLakes() async {
    if (_showLakes) {
      setState(() {
        _showLakes = false;
        _lakes = [];
        _lakePolygons = [];
      });
      _setStatus('Göl ve Göletler kapatıldı');
      return;
    }
    setState(() => _loading = true);
    _setStatus('Göl ve Göletler yükleniyor...');
    try {
      final gj = await _api.getLakes();
      final features = (gj['features'] as List?) ?? [];
      final polygons = <Polygon>[];
      final points = <WaterFeature>[];

      for (final raw in features) {
        if (raw is! Map<String, dynamic>) continue;
        if (!_isFeatureInIzmir(raw)) continue;

        final geom = raw['geometry'];
        if (geom is! Map<String, dynamic>) continue;

        final type = geom['type'];
        final coords = geom['coordinates'];

        if (type == 'Polygon' && coords is List && coords.isNotEmpty) {
          final outer = coords[0] as List;
          final pts = outer
              .whereType<List>()
              .where((c) => c.length >= 2)
              .map(
                (c) =>
                    LatLng((c[1] as num).toDouble(), (c[0] as num).toDouble()),
              )
              .toList();
          if (pts.isNotEmpty) {
            polygons.add(
              Polygon(
                points: pts,
                color: AppTheme.lake.withValues(alpha: 0.65),
                borderColor: const Color(0xFF001A2E),
                borderStrokeWidth: 2.5,
              ),
            );
          }
          continue;
        }

        if (type == 'MultiPolygon' && coords is List) {
          for (final poly in coords) {
            if (poly is! List || poly.isEmpty) continue;
            final outer = poly[0] as List;
            final pts = outer
                .whereType<List>()
                .where((c) => c.length >= 2)
                .map(
                  (c) => LatLng(
                    (c[1] as num).toDouble(),
                    (c[0] as num).toDouble(),
                  ),
                )
                .toList();
            if (pts.isNotEmpty) {
              polygons.add(
                Polygon(
                  points: pts,
                  color: AppTheme.lake.withValues(alpha: 0.65),
                  borderColor: const Color(0xFF001A2E),
                  borderStrokeWidth: 2.5,
                ),
              );
            }
          }
          continue;
        }

        if (type == 'Point') {
          points.add(WaterFeature.fromGeoJsonFeature(raw, 'lake'));
        }
      }

      setState(() {
        _lakes = points;
        _lakePolygons = polygons;
        _showLakes = true;
      });
      _setStatus('Göl ve Göletler: ${polygons.length + points.length}');
    } catch (e) {
      _setStatus('Göl ve Göletler hatası: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  // ─── Reset ────────────────────────────────────────────

  void _resetMap() {
    setState(() {
      _reservoirs = [];
      _waterSources = [];
      _waterTanks = [];
      _lakes = [];
      _lakePolygons = [];
      _showReservoirs = false;
      _showWaterSources = false;
      _showWaterTanks = false;
      _showLakes = false;
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

              // Water reservoirs
              if (_showReservoirs && _reservoirs.isNotEmpty)
                MarkerLayer(
                  markers: _reservoirs
                      .map(
                        (w) => Marker(
                          point: w.position,
                          width: 20,
                          height: 20,
                          child: Container(
                            decoration: BoxDecoration(
                              color: AppTheme.waterReservoir,
                              border: Border.all(
                                color: AppTheme.brandRed,
                                width: 2,
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.3),
                                  blurRadius: 4,
                                  offset: const Offset(0, 2),
                                ),
                              ],
                            ),
                          ),
                        ),
                      )
                      .toList(),
                ),

              // Water sources
              if (_showWaterSources && _waterSources.isNotEmpty)
                CircleLayer(
                  circles: _waterSources
                      .map(
                        (w) => CircleMarker(
                          point: w.position,
                          radius: 5,
                          color: AppTheme.waterSource.withValues(alpha: 0.7),
                          borderColor: AppTheme.waterSource,
                          borderStrokeWidth: 2,
                        ),
                      )
                      .toList(),
                ),

              // Water tanks
              if (_showWaterTanks && _waterTanks.isNotEmpty)
                MarkerLayer(
                  markers: _waterTanks
                      .map(
                        (w) => Marker(
                          point: w.position,
                          width: 18,
                          height: 18,
                          child: const Icon(
                            Icons.water_drop,
                            color: AppTheme.waterTank,
                            size: 18,
                          ),
                        ),
                      )
                      .toList(),
                ),

              // Lakes and ponds
              if (_showLakes && _lakePolygons.isNotEmpty)
                PolygonLayer(polygons: _lakePolygons),

              // Lakes represented as points (fallback)
              if (_showLakes && _lakes.isNotEmpty)
                CircleLayer(
                  circles: _lakes
                      .map(
                        (w) => CircleMarker(
                          point: w.position,
                          radius: 6,
                          color: AppTheme.lake.withValues(alpha: 0.65),
                          borderColor: const Color(0xFF001A2E),
                          borderStrokeWidth: 2,
                        ),
                      )
                      .toList(),
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
                      const Icon(
                        Icons.close,
                        color: Colors.white60,
                        size: 16,
                      ),
                    ],
                  ),
                ),
              ),
            ),

          // Detailed Info Panel (Bottom Left)
          if (_activeSpreadScenarioId != null)
            Positioned(
              bottom: 120,
              left: 16,
              child: _buildSpreadInfoPanel(),
            ),

          // ETA Box (Top Center - below alert)
          if (_activeSpreadScenarioId != null && (_etaMin != null || _distKm != null))
            Positioned(
              top: _spreadAlertMsg != null ? 70 : 12,
              left: 16,
              right: 16,
              child: Center(
                child: _buildEtaBox(),
              ),
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
          if (_statusText.isNotEmpty)
            Positioned(
              top: 8,
              left: 60,
              right: 60,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.92),
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.15),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Text(
                  _statusText,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF344044),
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ),

          // Map type toggle and Control panel overlapping the map directly
          Positioned(
            top: MediaQuery.of(context).padding.top + 12,
            right: 12,
            child: Column(
              children: [
                Material(
                  color: Colors.white.withValues(alpha: 0.9),
                  borderRadius: BorderRadius.circular(30),
                  elevation: 6,
                  child: InkWell(
                    borderRadius: BorderRadius.circular(30),
                    onTap: _showControlPanel,
                    child: const Padding(
                      padding: EdgeInsets.all(12),
                      child: Icon(
                        Icons.layers,
                        size: 24,
                        color: AppTheme.darkGreen,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Material(
                  color: Colors.white.withValues(alpha: 0.9),
                  borderRadius: BorderRadius.circular(30),
                  elevation: 6,
                  child: InkWell(
                    borderRadius: BorderRadius.circular(30),
                    onTap: () => setState(() => _useSatellite = !_useSatellite),
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Icon(
                        _useSatellite ? Icons.satellite_alt : Icons.map,
                        size: 24,
                        color: AppTheme.darkGreen,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          
          // Logout / Back to Login button
          Positioned(
            top: MediaQuery.of(context).padding.top + 12,
            left: 12,
            child: Material(
              color: Colors.white.withValues(alpha: 0.9),
              borderRadius: BorderRadius.circular(30),
              elevation: 6,
              child: InkWell(
                borderRadius: BorderRadius.circular(30),
                onTap: () async {
                  await context.read<AuthService>().logout();
                  if (context.mounted) {
                    Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(builder: (_) => const LoginScreen()),
                    );
                  }
                },
                child: const Padding(
                  padding: EdgeInsets.all(12),
                  child: Icon(
                    Icons.logout_rounded,
                    size: 24,
                    color: AppTheme.brandRed,
                  ),
                ),
              ),
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

  void _showControlPanel() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => MapControlPanel(
        showReservoirs: _showReservoirs,
        showWaterSources: _showWaterSources,
        showWaterTanks: _showWaterTanks,
        showLakes: _showLakes,
        hasActiveSpread: _activeSpreadScenarioId != null,
        onToggleReservoirs: () {
          Navigator.pop(ctx);
          _toggleReservoirs();
        },
        onToggleWaterSources: () {
          Navigator.pop(ctx);
          _toggleWaterSources();
        },
        onToggleWaterTanks: () {
          Navigator.pop(ctx);
          _toggleWaterTanks();
        },
        onToggleLakes: () {
          Navigator.pop(ctx);
          _toggleLakes();
        },
        onShowSpreadScenario: () {
          Navigator.pop(ctx);
          if (_activeSpreadScenarioId != null) {
            // Stop tracking if already active
            _stopSpreadTracking();
          } else {
            // Enable picking mode
            setState(() {
              _isPickingSpreadLocation = true;
              _setStatus('Haritadan yangın başlangıç noktası seçin');
            });
          }
        },
        onShowSpreadList: () {
          Navigator.pop(ctx);
          _loadSpreadScenarios();
        },
        onReset: () {
          Navigator.pop(ctx);
          _resetMap();
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
    final windKmh = (_windSpeedMs != null ? (_windSpeedMs! * 3.6) : 0.0).toStringAsFixed(1);
    final spreadRateKmh = (_scenarioProps?['spread_rate_ms'] != null ? (_scenarioProps!['spread_rate_ms'] * 3.6) : 0.0).toStringAsFixed(2);
    final frontDist = (_scenarioProps?['front_radius_km'] as num?)?.toDouble().toStringAsFixed(2) ?? '-';
    final humidity = (_scenarioWeather?['humidity'] as num?)?.toDouble().toStringAsFixed(0) ?? '-';
    final temp = (_scenarioWeather?['temperature_c'] as num?)?.toDouble().toStringAsFixed(1) ?? '-';

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
          _buildInfoRow('Süre:', '${(_elapsedMinutes ?? 0).toStringAsFixed(0)} dk'),
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
          _buildInfoRow('Rüzgar:', '$windKmh km/sa  ${_windDir?.toStringAsFixed(0) ?? '-'}°'),
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
}
