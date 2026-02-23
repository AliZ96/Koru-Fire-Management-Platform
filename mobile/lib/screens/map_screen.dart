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
import '../widgets/map_control_panel.dart';
import '../widgets/map_legend.dart';
import 'login_screen.dart';

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  final MapController _mapCtrl = MapController();

  // Layer data
  List<FirePoint> _fires = [];
  List<FireRiskPoint> _fireRiskPoints = [];
  List<WaterFeature> _reservoirs = [];
  List<WaterFeature> _waterSources = [];
  List<WaterFeature> _waterTanks = [];
  List<WaterFeature> _lakes =
      []; // ignore: unused_field – rendered when backend provides lake data
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

  @override
  void initState() {
    super.initState();
    _api = ApiService();
    // Set token if available
    final auth = context.read<AuthService>();
    if (auth.user?.accessToken != null) {
      _api.setToken(auth.user!.accessToken);
    }
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
        _heatmapCells = features.cast<Map<String, dynamic>>();
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
      });
      _setStatus('Göl ve Göletler kapatıldı');
      return;
    }
    setState(() => _loading = true);
    _setStatus('Göl ve Göletler yükleniyor...');
    // Lakes are loaded from static data — try API first
    try {
      // Use water sources endpoint as proxy for lakes
      // In real app this would be a separate endpoint or bundled geojson
      setState(() {
        _showLakes = true;
      });
      _setStatus('Göl ve Göletler: (statik veri gerekli)');
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
      _statusText = 'Harita sıfırlandı';
    });
    _mapCtrl.move(const LatLng(38.42, 27.14), 8);
  }

  // ─── Build ────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final username = auth.user?.username ?? 'Kullanıcı';
    final userRole = auth.user?.role ?? 'user';
    final roleLabel = userRole == 'admin' ? 'Admin' : 'Kullanıcı';

    return Scaffold(
      // AppBar matching web header
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text(
          'KORU Yangın Önleme Platformu',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
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
                    content: Text('Profil: $username ($roleLabel)'),
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
              const PopupMenuItem(
                value: 'profile',
                child: Row(
                  children: [Text('👤'), SizedBox(width: 8), Text('Profil')],
                ),
              ),
              const PopupMenuItem(
                value: 'logout',
                child: Row(
                  children: [
                    Text('🚪'),
                    SizedBox(width: 8),
                    Text('Oturum Kapat'),
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
              child: MapLegend(type: _activeLegend!),
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
              label: 'İzmir Yangınları',
              onTap: () {
                Navigator.pop(context);
                _toggleLiveTracking();
              },
            ),
            _drawerItem(
              icon: Icons.volunteer_activism,
              label: 'AFAD Gönüllüsü olun',
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
              label: 'Bize Ulaşın',
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
                'KORU Yangın Önleme Platformu',
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
