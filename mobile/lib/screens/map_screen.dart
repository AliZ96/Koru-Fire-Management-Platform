import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../config/app_theme.dart';
import '../models/fire_data.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../services/map_data_service.dart';
import '../widgets/map_control_panel.dart';
import '../widgets/map_legend.dart';
import 'login_screen.dart';
import 'data_visualization_screen.dart';

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
  List<FirePoint> _fires = [];
  List<FireRiskPoint> _fireRiskPoints = [];
  List<WaterFeature> _reservoirs = [];
  List<WaterFeature> _waterSources = [];
  List<WaterFeature> _waterTanks = [];
  List<WaterFeature> _lakes = [];
  List<Polygon> _lakePolygons = [];
  WindData? _windData; // ignore: unused_field – reserved for wind overlay

  // Layer visibility toggles
  bool _showFires = false;
  bool _showFireRisk = false;
  bool _showHeatmap = false;
  bool _showReservoirs = false;
  bool _showWaterSources = false;
  bool _showWaterTanks = false;
  bool _showLakes = false;

  // Live tracking
  bool _isLiveTracking = false;
  Timer? _liveTimer;

  // Loading state
  bool _loading = false;
  String _statusText = '';

  // Map type
  bool _useSatellite = true;

  // Heatmap grid data (polygons)
  List<Map<String, dynamic>> _heatmapCells = [];

  // Selected fire day range
  int _dayRange = 1;

  // Legend type
  String? _activeLegend; // 'fire_risk', 'heatmap', null

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
      _loadInitialOptimizedPoints();
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

  Future<void> _loadInitialOptimizedPoints() async {
    if (_showFireRisk || _loading) return;
    await _toggleFireRisk();
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
    _liveTimer?.cancel();
    _mapCtrl.dispose();
    super.dispose();
  }

  void _setStatus(String msg) {
    if (mounted) setState(() => _statusText = msg);
  }

  // ─── Fire data loading ───────────────────────────────

  Future<void> _loadFires() async {
    setState(() => _loading = true);
    _setStatus('Yangınlar yükleniyor...');
    try {
      final gj = await _api.getFires(dayRange: _dayRange);
      final features = (gj['features'] as List?) ?? [];
      final fires = features
          .map((f) => FirePoint.fromGeoJsonFeature(f as Map<String, dynamic>))
          .where((f) => _isInIzmir(f.position.latitude, f.position.longitude))
          .toList();
      setState(() {
        _fires = fires;
        _showFires = true;
      });
      _setStatus('İzmir Yangınları: ${fires.length}');
    } catch (e) {
      _setStatus('Yangın yükleme hatası: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  void _toggleLiveTracking() {
    if (_isLiveTracking) {
      // Stop
      _liveTimer?.cancel();
      _liveTimer = null;
      setState(() {
        _isLiveTracking = false;
        _showFires = false;
        _fires = [];
      });
      _setStatus('Canlı takip durduruldu');
    } else {
      // Start
      setState(() => _isLiveTracking = true);
      _loadLiveData();
      _liveTimer = Timer.periodic(
        const Duration(seconds: 30),
        (_) => _loadLiveData(),
      );
    }
  }

  Future<void> _loadLiveData() async {
    try {
      final gj = await _api.getFires(dayRange: 1);
      final features = (gj['features'] as List?) ?? [];
      final fires = features
          .map((f) => FirePoint.fromGeoJsonFeature(f as Map<String, dynamic>))
          .where((f) => _isInIzmir(f.position.latitude, f.position.longitude))
          .toList();
      final now = DateTime.now();
      final timeStr =
          '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
      setState(() {
        _fires = fires;
        _showFires = true;
      });
      _setStatus('🟢 Canlı Yangınlar: ${fires.length} | Güncelleme: $timeStr');
    } catch (e) {
      _setStatus('Canlı takip hatası: $e');
    }
  }

  // ─── Fire Risk ML ─────────────────────────────────────

  Future<void> _toggleFireRisk() async {
    if (_showFireRisk) {
      setState(() {
        _showFireRisk = false;
        _fireRiskPoints = [];
        _activeLegend = _showHeatmap ? 'heatmap' : null;
      });
      _setStatus('Yangın risk kapatıldı');
      return;
    }

    setState(() => _loading = true);
    _setStatus('ML Yangın Risk Noktaları yükleniyor...');
    try {
      final gj = await _api.getFireRiskPoints(limit: 50000);
      final features = (gj['features'] as List?) ?? [];
      final points = features
          .map(
            (f) => FireRiskPoint.fromGeoJsonFeature(f as Map<String, dynamic>),
          )
          .where((p) => _isInIzmir(p.position.latitude, p.position.longitude))
          .toList();
      setState(() {
        _fireRiskPoints = points;
        _showFireRisk = true;
        _activeLegend = 'fire_risk';
      });
      _setStatus('ML Yangın Risk Noktaları: ${points.length}');
    } catch (e) {
      _setStatus('Yangın risk hatası: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  // ─── Heatmap ──────────────────────────────────────────

  Future<void> _toggleHeatmap() async {
    if (_showHeatmap) {
      setState(() {
        _showHeatmap = false;
        _heatmapCells = [];
        _activeLegend = _showFireRisk ? 'fire_risk' : null;
      });
      _setStatus('Heatmap kapatıldı');
      return;
    }

    setState(() => _loading = true);
    _setStatus('Heatmap yükleniyor...');
    try {
      final gj = await _api.getFireRiskHeatmap(cellSize: 0.05);
      final features = (gj['features'] as List?) ?? [];
      setState(() {
        _heatmapCells = features
            .cast<Map<String, dynamic>>()
            .where(_isFeatureInIzmir)
            .toList();
        _showHeatmap = true;
        _activeLegend = 'heatmap';
      });
      _setStatus('Heatmap: ${features.length} hücre');
    } catch (e) {
      _setStatus('Heatmap hatası: $e');
    } finally {
      setState(() => _loading = false);
    }
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
    _liveTimer?.cancel();
    _liveTimer = null;
    setState(() {
      _fires = [];
      _fireRiskPoints = [];
      _heatmapCells = [];
      _reservoirs = [];
      _waterSources = [];
      _waterTanks = [];
      _lakes = [];
      _lakePolygons = [];
      _showFires = false;
      _showFireRisk = false;
      _showHeatmap = false;
      _showReservoirs = false;
      _showWaterSources = false;
      _showWaterTanks = false;
      _showLakes = false;
      _isLiveTracking = false;
      _activeLegend = null;
      _dayRange = 1;
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
      // AppBar matching web header
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          _t('header_title', 'KORU Yangın Önleme Platformu'),
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
        ),
        backgroundColor: AppTheme.brandRed,
        foregroundColor: Colors.white,
        actions: [
          PopupMenuButton<String>(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '$roleLabel - $username',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                  const Icon(
                    Icons.arrow_drop_down,
                    color: Colors.white,
                    size: 18,
                  ),
                ],
              ),
            ),
            onSelected: (value) async {
              if (value == 'profile') {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      '${_t('profile_label', 'Profil')}: $username ($roleLabel)',
                    ),
                    backgroundColor: AppTheme.brandRed,
                  ),
                );
              } else if (value == 'logout') {
                await auth.logout();
                if (context.mounted) {
                  Navigator.pushAndRemoveUntil(
                    context,
                    MaterialPageRoute(builder: (_) => const LoginScreen()),
                    (_) => false,
                  );
                }
              }
            },
            itemBuilder: (_) => [
              PopupMenuItem(
                value: 'profile',
                child: Row(
                  children: [
                    const Text('👤'),
                    const SizedBox(width: 8),
                    Text(_t('profile_label', 'Profil')),
                  ],
                ),
              ),
              PopupMenuItem(
                value: 'logout',
                child: Row(
                  children: [
                    const Text('🚪'),
                    const SizedBox(width: 8),
                    Text(_t('logout_label', 'Oturum Kapat')),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),

      // Drawer (sidebar menu)
      drawer: _buildDrawer(context),

      body: Stack(
        children: [
          // Map
          FlutterMap(
            mapController: _mapCtrl,
            options: MapOptions(
              initialCenter: const LatLng(38.42, 27.14),
              initialZoom: 8,
              maxZoom: 19,
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

              // Heatmap polygon layer
              if (_showHeatmap && _heatmapCells.isNotEmpty)
                PolygonLayer(polygons: _buildHeatmapPolygons()),

              // Fire risk circle markers
              if (_showFireRisk && _fireRiskPoints.isNotEmpty)
                CircleLayer(circles: _buildFireRiskCircles()),

              // Fire points
              if (_showFires && _fires.isNotEmpty)
                CircleLayer(
                  circles: _fires.map((f) {
                    final color = AppTheme.fireConfidenceColor(
                      f.confidence ?? 'l',
                    );
                    return CircleMarker(
                      point: f.position,
                      radius: 5,
                      color: color.withValues(alpha: 0.8),
                      borderColor: color,
                      borderStrokeWidth: 1,
                    );
                  }).toList(),
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
            ],
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

          // Map type toggle
          Positioned(
            top: 8,
            left: 8,
            child: Material(
              color: Colors.white,
              borderRadius: BorderRadius.circular(8),
              elevation: 4,
              child: InkWell(
                borderRadius: BorderRadius.circular(8),
                onTap: () => setState(() => _useSatellite = !_useSatellite),
                child: Padding(
                  padding: const EdgeInsets.all(8),
                  child: Icon(
                    _useSatellite ? Icons.satellite_alt : Icons.map,
                    size: 22,
                    color: AppTheme.brandRed,
                  ),
                ),
              ),
            ),
          ),

          // Legend
          if (_activeLegend != null)
            Positioned(
              bottom: 16,
              right: 16,
              child: MapLegend(type: _activeLegend!, tr: _t),
            ),

          // Control panel toggle
          Positioned(
            top: 8,
            right: 8,
            child: Material(
              color: Colors.white,
              borderRadius: BorderRadius.circular(8),
              elevation: 4,
              child: InkWell(
                borderRadius: BorderRadius.circular(8),
                onTap: _showControlPanel,
                child: const Padding(
                  padding: EdgeInsets.all(8),
                  child: Icon(
                    Icons.settings,
                    size: 22,
                    color: AppTheme.brandRed,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),

      // Footer contact
      bottomNavigationBar: Container(
        height: 50,
        color: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: Row(
          children: [
            Expanded(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _contactItem('Tel:', '153'),
                    const SizedBox(width: 12),
                    _contactItem('Faks:', '(0232) 293 39 95'),
                    const SizedBox(width: 12),
                    GestureDetector(
                      onTap: () =>
                          launchUrl(Uri.parse('mailto:him@izmir.bel.tr')),
                      child: Text(
                        'E-Posta: him@izmir.bel.tr',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.brandRed,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),

      // Floating action button for data visualization
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const DataVisualizationScreen()),
          );
        },
        icon: const Icon(Icons.analytics),
        label: const Text('Veriler'),
        tooltip: 'Risk Zonları ve Erişilebilirlik Verilerini Görüntüle',
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

  List<CircleMarker> _buildFireRiskCircles() {
    return _fireRiskPoints.map((p) {
      double radius;
      double opacity;
      Color color;

      switch (p.riskClass) {
        case 'HIGH_RISK':
          radius = 8;
          opacity = 0.85;
          color = AppTheme.riskHigh;
          break;
        case 'MEDIUM_RISK':
          radius = 6;
          opacity = 0.75;
          color = AppTheme.riskMedium;
          break;
        case 'LOW_RISK':
          radius = 4;
          opacity = 0.6;
          color = AppTheme.riskLow;
          break;
        default:
          radius = 3;
          opacity = 0.4;
          color = AppTheme.riskSafe;
      }

      return CircleMarker(
        point: p.position,
        radius: radius,
        color: color.withValues(alpha: opacity),
        borderColor: color,
        borderStrokeWidth: 1,
      );
    }).toList();
  }

  List<Polygon> _buildHeatmapPolygons() {
    final polys = <Polygon>[];
    for (final cell in _heatmapCells) {
      try {
        final geom = cell['geometry'] as Map<String, dynamic>;
        if (geom['type'] != 'Polygon') continue;
        final coords = geom['coordinates'][0] as List;
        final props = cell['properties'] as Map<String, dynamic>? ?? {};
        final score = (props['combined_risk_score'] as num?)?.toDouble() ?? 0.0;

        Color color;
        double opacity;
        if (score >= 0.8) {
          color = const Color(0xFF8B0000);
          opacity = 0.85;
        } else if (score >= 0.6) {
          color = const Color(0xFFD70000);
          opacity = 0.80;
        } else if (score >= 0.4) {
          color = const Color(0xFFFF4500);
          opacity = 0.75;
        } else if (score >= 0.2) {
          color = const Color(0xFFFFA500);
          opacity = 0.70;
        } else {
          color = const Color(0xFFFFFF00);
          opacity = 0.65;
        }

        final points = coords
            .map(
              (c) => LatLng((c[1] as num).toDouble(), (c[0] as num).toDouble()),
            )
            .toList();

        polys.add(
          Polygon(
            points: points,
            color: color.withValues(alpha: opacity),
            borderColor: color.withValues(alpha: 0.8),
            borderStrokeWidth: 0.5,
          ),
        );
      } catch (_) {}
    }
    return polys;
  }

  // ─── Control panel bottom sheet ───────────────────────

  void _showControlPanel() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => MapControlPanel(
        dayRange: _dayRange,
        isLiveTracking: _isLiveTracking,
        showFires: _showFires,
        showFireRisk: _showFireRisk,
        showHeatmap: _showHeatmap,
        showReservoirs: _showReservoirs,
        showWaterSources: _showWaterSources,
        showWaterTanks: _showWaterTanks,
        showLakes: _showLakes,
        onDayRangeChanged: (v) => setState(() => _dayRange = v),
        onLoadFires: () {
          Navigator.pop(ctx);
          _loadFires();
        },
        onToggleLive: () {
          Navigator.pop(ctx);
          _toggleLiveTracking();
        },
        onToggleFireRisk: () {
          Navigator.pop(ctx);
          _toggleFireRisk();
        },
        onToggleHeatmap: () {
          Navigator.pop(ctx);
          _toggleHeatmap();
        },
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
              icon: Icons.local_fire_department,
              label: _t('menu_fires', 'İzmir Yangınları'),
              onTap: () {
                Navigator.pop(context);
                _toggleLiveTracking();
              },
            ),
            _drawerItem(
              icon: Icons.volunteer_activism,
              label: _t('menu_volunteer', 'AFAD Gönüllüsü olun'),
              onTap: () {
                Navigator.pop(context);
                launchUrl(
                  Uri.parse('https://gonullu.afad.gov.tr/'),
                  mode: LaunchMode.externalApplication,
                );
              },
            ),
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
}
