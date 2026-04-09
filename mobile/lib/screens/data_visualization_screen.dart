import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/map_data_service.dart';
import '../widgets/data_display_widgets.dart';

/// Screen showing detailed risk zones and accessibility data
class DataVisualizationScreen extends StatefulWidget {
  const DataVisualizationScreen({super.key});

  @override
  State<DataVisualizationScreen> createState() =>
      _DataVisualizationScreenState();
}

class _DataVisualizationScreenState extends State<DataVisualizationScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadData();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    final service = context.read<MapDataService>();
    await Future.wait([
      service.loadRiskZones(),
      service.loadAccessibilityZones(),
      service.loadIntegratedZones(),
      service.loadRiskStatistics(),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Harita Verileri'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Risk Zonları'),
            Tab(text: 'Erişilebilirlik'),
            Tab(text: 'İstatistikler'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildRiskZonesTab(),
          _buildAccessibilityTab(),
          _buildStatisticsTab(),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _loadData,
        tooltip: 'Yenile',
        child: const Icon(Icons.refresh),
      ),
    );
  }

  Widget _buildRiskZonesTab() {
    return Consumer<MapDataService>(
      builder: (context, mapDataService, _) {
        return SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              RiskDataCard(
                title: 'Yüksek Risk Zonları',
                zones: mapDataService.filterRiskZonesByClass('HIGH_RISK'),
                loading: mapDataService.loadingRiskZones,
                error: mapDataService.lastError,
                onRefresh: () => mapDataService.loadRiskZones(),
              ),
              const SizedBox(height: 16),
              RiskDataCard(
                title: 'Orta Risk Zonları',
                zones: mapDataService.filterRiskZonesByClass('MEDIUM_RISK'),
                loading: mapDataService.loadingRiskZones,
                error: mapDataService.lastError,
              ),
              const SizedBox(height: 16),
              RiskDataCard(
                title: 'Düşük Risk Zonları',
                zones: mapDataService.filterRiskZonesByClass('LOW_RISK'),
                loading: mapDataService.loadingRiskZones,
                error: mapDataService.lastError,
              ),
              const SizedBox(height: 16),
              RiskDataCard(
                title: 'Güvenli Bölgeler',
                zones: mapDataService.filterRiskZonesByClass('SAFE_UNBURNABLE'),
                loading: mapDataService.loadingRiskZones,
                error: mapDataService.lastError,
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildAccessibilityTab() {
    return Consumer<MapDataService>(
      builder: (context, mapDataService, _) {
        return SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              AccessibilityDataCard(
                title: 'Yüksek Erişilebilirlik Alanları',
                zones: mapDataService.filterAccessibilityByClass('HIGH'),
                loading: mapDataService.loadingAccessibility,
                error: mapDataService.lastError,
                onRefresh: () => mapDataService.loadAccessibilityZones(),
              ),
              const SizedBox(height: 16),
              AccessibilityDataCard(
                title: 'Orta Erişilebilirlik Alanları',
                zones: mapDataService.filterAccessibilityByClass('MEDIUM'),
                loading: mapDataService.loadingAccessibility,
                error: mapDataService.lastError,
              ),
              const SizedBox(height: 16),
              AccessibilityDataCard(
                title: 'Düşük Erişilebilirlik Alanları',
                zones: mapDataService.filterAccessibilityByClass('LOW'),
                loading: mapDataService.loadingAccessibility,
                error: mapDataService.lastError,
              ),
              const SizedBox(height: 16),
              AccessibilityDataCard(
                title: 'Erişim Olmayan Alanlar',
                zones: mapDataService.filterAccessibilityByClass('NO_ACCESS'),
                loading: mapDataService.loadingAccessibility,
                error: mapDataService.lastError,
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildStatisticsTab() {
    return Consumer<MapDataService>(
      builder: (context, mapDataService, _) {
        return SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              RiskStatisticsCard(
                statistics: mapDataService.statistics,
                loading: mapDataService.loadingStatistics,
                error: mapDataService.lastError,
                onRefresh: () => mapDataService.loadRiskStatistics(),
              ),
              const SizedBox(height: 32),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Ayarlar',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton.icon(
                        onPressed: () => mapDataService.refreshAll(),
                        icon: const Icon(Icons.refresh),
                        label: const Text('Tüm Verileri Yenile'),
                      ),
                      const SizedBox(height: 12),
                      ElevatedButton.icon(
                        onPressed: () => mapDataService.clearCache(),
                        icon: const Icon(Icons.delete_outline),
                        label: const Text('Önbelleği Temizle'),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
