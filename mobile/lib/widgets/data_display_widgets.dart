import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/accessibility_data.dart';
import '../services/map_data_service.dart';

/// Widget for displaying risk zones and accessibility data
class RiskDataCard extends StatelessWidget {
  final String title;
  final List<RiskZone> zones;
  final bool loading;
  final String? error;
  final VoidCallback? onRefresh;

  const RiskDataCard({
    super.key,
    required this.title,
    required this.zones,
    this.loading = false,
    this.error,
    this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return Card(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const CircularProgressIndicator(),
                const SizedBox(height: 12),
                Text('$title yükleniyor...'),
              ],
            ),
          ),
        ),
      );
    }

    if (error != null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: Colors.red),
              const SizedBox(height: 8),
              Text(
                error!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.red),
              ),
              const SizedBox(height: 12),
              if (onRefresh != null)
                ElevatedButton(
                  onPressed: onRefresh,
                  child: const Text('Yeniden Dene'),
                ),
            ],
          ),
        ),
      );
    }

    if (zones.isEmpty) {
      return Card(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.info_outline),
                const SizedBox(height: 8),
                Text('$title bulunamadı'),
              ],
            ),
          ),
        ),
      );
    }

    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  '${zones.length} bölge',
                  style: TextStyle(color: Colors.grey[600], fontSize: 14),
                ),
              ],
            ),
          ),
          const Divider(height: 0),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: zones.length,
            separatorBuilder: (_, __) => const Divider(height: 0),
            itemBuilder: (context, index) {
              final zone = zones[index];
              return RiskZoneListTile(zone: zone);
            },
          ),
        ],
      ),
    );
  }
}

/// List tile for a single risk zone
class RiskZoneListTile extends StatelessWidget {
  final RiskZone zone;

  const RiskZoneListTile({super.key, required this.zone});

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Container(
        width: 12,
        height: 12,
        decoration: BoxDecoration(
          color: zone.colorFromRisk,
          shape: BoxShape.circle,
        ),
      ),
      title: Text(zone.riskLabel),
      subtitle: Text(
        '${zone.pointCount} nokta • Ort. Risk: ${(zone.avgRiskScore * 100).toStringAsFixed(0)}%',
      ),
      trailing: Tooltip(
        message:
            'Koordinatlar: ${zone.center.latitude.toStringAsFixed(4)}, ${zone.center.longitude.toStringAsFixed(4)}',
        child: const Icon(Icons.info_outline, size: 18),
      ),
    );
  }
}

/// Widget for displaying accessibility zones
class AccessibilityDataCard extends StatelessWidget {
  final String title;
  final List<AccessibilityZone> zones;
  final bool loading;
  final String? error;
  final VoidCallback? onRefresh;

  const AccessibilityDataCard({
    super.key,
    required this.title,
    required this.zones,
    this.loading = false,
    this.error,
    this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return Card(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const CircularProgressIndicator(),
                const SizedBox(height: 12),
                Text('$title yükleniyor...'),
              ],
            ),
          ),
        ),
      );
    }

    if (error != null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: Colors.red),
              const SizedBox(height: 8),
              Text(
                error!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.red),
              ),
              const SizedBox(height: 12),
              if (onRefresh != null)
                ElevatedButton(
                  onPressed: onRefresh,
                  child: const Text('Yeniden Dene'),
                ),
            ],
          ),
        ),
      );
    }

    if (zones.isEmpty) {
      return Card(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.info_outline),
                const SizedBox(height: 8),
                Text('$title bulunamadı'),
              ],
            ),
          ),
        ),
      );
    }

    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  '${zones.length} bölge',
                  style: TextStyle(color: Colors.grey[600], fontSize: 14),
                ),
              ],
            ),
          ),
          const Divider(height: 0),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: zones.length,
            separatorBuilder: (_, __) => const Divider(height: 0),
            itemBuilder: (context, index) {
              final zone = zones[index];
              return AccessibilityZoneListTile(zone: zone);
            },
          ),
        ],
      ),
    );
  }
}

/// List tile for a single accessibility zone
class AccessibilityZoneListTile extends StatelessWidget {
  final AccessibilityZone zone;

  const AccessibilityZoneListTile({super.key, required this.zone});

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Container(
        width: 12,
        height: 12,
        decoration: BoxDecoration(
          color: zone.colorFromAccessibility,
          shape: BoxShape.circle,
        ),
      ),
      title: Text(zone.accessibilityLabel),
      subtitle: Text(
        '${zone.pointCount} nokta • Erişilebilirlik: ${(zone.accessibility * 100).toStringAsFixed(0)}%',
      ),
      trailing: Tooltip(
        message:
            'Koordinatlar: ${zone.center.latitude.toStringAsFixed(4)}, ${zone.center.longitude.toStringAsFixed(4)}',
        child: const Icon(Icons.info_outline, size: 18),
      ),
    );
  }
}

/// Summary card showing statistics
class RiskStatisticsCard extends StatelessWidget {
  final FireRiskStatistics? statistics;
  final bool loading;
  final String? error;
  final VoidCallback? onRefresh;

  const RiskStatisticsCard({
    super.key,
    this.statistics,
    this.loading = false,
    this.error,
    this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return Card(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: const [
                CircularProgressIndicator(),
                SizedBox(height: 12),
                Text('İstatistikler yükleniyor...'),
              ],
            ),
          ),
        ),
      );
    }

    if (error != null || statistics == null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: Colors.red),
              const SizedBox(height: 8),
              Text(
                error ?? 'İstatistikler yüklenemedi',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.red),
              ),
              const SizedBox(height: 12),
              if (onRefresh != null)
                ElevatedButton(
                  onPressed: onRefresh,
                  child: const Text('Yeniden Dene'),
                ),
            ],
          ),
        ),
      );
    }

    final stats = statistics!;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Yangın Risk İstatistikleri',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            _StatisticRow(
              label: 'Toplam Noktalar',
              value: '${stats.totalPoints}',
            ),
            _StatisticRow(
              label: 'Yüksek Risk',
              value: stats.highRiskCount.toString(),
              color: const Color(0xFF8b0000),
            ),
            _StatisticRow(
              label: 'Orta Risk',
              value: stats.mediumRiskCount.toString(),
              color: const Color(0xFFe74c3c),
            ),
            _StatisticRow(
              label: 'Düşük Risk',
              value: stats.lowRiskCount.toString(),
              color: const Color(0xFFf39c12),
            ),
            _StatisticRow(
              label: 'Güvenli',
              value: stats.safeCount.toString(),
              color: const Color(0xFF2ecc71),
            ),
            const Divider(),
            _StatisticRow(
              label: 'Ortalama Yangın Olasılığı',
              value:
                  '${(stats.averageFireProbability * 100).toStringAsFixed(1)}%',
            ),
            _StatisticRow(
              label: 'Ortalama Risk Skoru',
              value: (stats.averageCombinedRiskScore * 100).toStringAsFixed(0),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatisticRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? color;

  const _StatisticRow({required this.label, required this.value, this.color});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Row(
            children: [
              if (color != null) ...[
                Container(
                  width: 12,
                  height: 12,
                  decoration: BoxDecoration(
                    color: color,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
              ],
              Text(value, style: const TextStyle(fontWeight: FontWeight.bold)),
            ],
          ),
        ],
      ),
    );
  }
}
