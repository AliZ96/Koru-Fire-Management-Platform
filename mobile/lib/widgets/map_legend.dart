import 'package:flutter/material.dart';
import '../config/app_theme.dart';

/// Shows a legend overlay on the map for the active risk/heatmap layer.
class MapLegend extends StatelessWidget {
  final String type; // 'fire_risk' or 'heatmap'

  const MapLegend({super.key, required this.type});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      constraints: const BoxConstraints(maxWidth: 180),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.95),
        borderRadius: BorderRadius.circular(8),
        boxShadow: [
          BoxShadow(color: Colors.black.withValues(alpha: 0.2), blurRadius: 15),
        ],
      ),
      child: type == 'fire_risk'
          ? _buildFireRiskLegend()
          : _buildHeatmapLegend(),
    );
  }

  Widget _buildFireRiskLegend() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Yangın Risk Sınıfları',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 11),
        ),
        const SizedBox(height: 6),
        _legendRow(AppTheme.riskHigh, 'Yüksek Risk', size: 12),
        _legendRow(AppTheme.riskMedium, 'Orta Risk', size: 10),
        _legendRow(AppTheme.riskLow, 'Düşük Risk', size: 8),
        _legendRow(AppTheme.riskSafe, 'Güvenli', size: 6),
      ],
    );
  }

  Widget _buildHeatmapLegend() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Yangın Risk Heatmap',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 11),
        ),
        const SizedBox(height: 6),
        _legendSquare(const Color(0xFF8B0000), 'Çok Yüksek (≥0.8)'),
        _legendSquare(const Color(0xFFD70000), 'Yüksek (≥0.6)'),
        _legendSquare(const Color(0xFFFF4500), 'Orta (≥0.4)'),
        _legendSquare(const Color(0xFFFFA500), 'Düşük (≥0.2)'),
        _legendSquare(
          const Color(0xFFFFFF00),
          'Çok Düşük (<0.2)',
          border: true,
        ),
      ],
    );
  }

  Widget _legendRow(Color color, String label, {double size = 12}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Container(
            width: size,
            height: size,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 6),
          Expanded(child: Text(label, style: const TextStyle(fontSize: 10))),
        ],
      ),
    );
  }

  Widget _legendSquare(Color color, String label, {bool border = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Container(
            width: 14,
            height: 14,
            decoration: BoxDecoration(
              color: color,
              border: border ? Border.all(color: Colors.grey) : null,
            ),
          ),
          const SizedBox(width: 6),
          Expanded(child: Text(label, style: const TextStyle(fontSize: 10))),
        ],
      ),
    );
  }
}
