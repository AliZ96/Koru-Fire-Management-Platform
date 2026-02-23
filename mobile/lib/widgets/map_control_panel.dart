import 'package:flutter/material.dart';
import '../config/app_theme.dart';

/// Bottom sheet control panel for the map — mirrors the web panel.
class MapControlPanel extends StatelessWidget {
  final int dayRange;
  final bool isLiveTracking;
  final bool showFires;
  final bool showFireRisk;
  final bool showHeatmap;
  final bool showReservoirs;
  final bool showWaterSources;
  final bool showWaterTanks;
  final bool showLakes;

  final ValueChanged<int> onDayRangeChanged;
  final VoidCallback onLoadFires;
  final VoidCallback onToggleLive;
  final VoidCallback onToggleFireRisk;
  final VoidCallback onToggleHeatmap;
  final VoidCallback onToggleReservoirs;
  final VoidCallback onToggleWaterSources;
  final VoidCallback onToggleWaterTanks;
  final VoidCallback onToggleLakes;
  final VoidCallback onReset;

  const MapControlPanel({
    super.key,
    required this.dayRange,
    required this.isLiveTracking,
    required this.showFires,
    required this.showFireRisk,
    required this.showHeatmap,
    required this.showReservoirs,
    required this.showWaterSources,
    required this.showWaterTanks,
    required this.showLakes,
    required this.onDayRangeChanged,
    required this.onLoadFires,
    required this.onToggleLive,
    required this.onToggleFireRisk,
    required this.onToggleHeatmap,
    required this.onToggleReservoirs,
    required this.onToggleWaterSources,
    required this.onToggleWaterTanks,
    required this.onToggleLakes,
    required this.onReset,
  });

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.55,
      minChildSize: 0.3,
      maxChildSize: 0.85,
      builder: (context, scrollController) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
            boxShadow: [
              BoxShadow(
                color: Colors.black26,
                blurRadius: 16,
                offset: Offset(0, -2),
              ),
            ],
          ),
          child: ListView(
            controller: scrollController,
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            children: [
              // Handle bar
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.grey[300],
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),

              // ── İzmir Yangınları section ──
              _sectionTitle('İzmir Yangınları'),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Text(
                    'Yangın Aralığı',
                    style: TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.grey[300]!),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<int>(
                        value: dayRange,
                        isDense: true,
                        style: const TextStyle(
                          fontSize: 12,
                          color: Colors.black87,
                        ),
                        items: const [
                          DropdownMenuItem(
                            value: 1,
                            child: Text('Son 24 saat'),
                          ),
                          DropdownMenuItem(
                            value: 7,
                            child: Text('Son 1 hafta'),
                          ),
                        ],
                        onChanged: (v) {
                          if (v != null) onDayRangeChanged(v);
                        },
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: _outlineBtn(
                      label: 'Göster',
                      active: showFires,
                      onTap: onLoadFires,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _primaryBtn(
                      label: isLiveTracking
                          ? '🟢 Canlı Takip'
                          : '🔴 Canlı Takip',
                      onTap: onToggleLive,
                    ),
                  ),
                ],
              ),

              const Divider(height: 28),

              // ── Risk ve Katmanlar section ──
              _sectionTitle('Risk ve Katmanlar'),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _outlineBtn(
                    label: 'Riskli Bölgeler',
                    active: showFireRisk,
                    onTap: onToggleFireRisk,
                  ),
                  _outlineBtn(
                    label: 'Isıl Harita',
                    active: showHeatmap,
                    onTap: onToggleHeatmap,
                  ),
                  _outlineBtn(
                    label: 'Su Rezervuarları',
                    active: showReservoirs,
                    onTap: onToggleReservoirs,
                  ),
                  _outlineBtn(
                    label: 'Su Kaynakları',
                    active: showWaterSources,
                    onTap: onToggleWaterSources,
                  ),
                  _outlineBtn(
                    label: 'Su Tankları',
                    active: showWaterTanks,
                    onTap: onToggleWaterTanks,
                  ),
                  _outlineBtn(
                    label: 'Göl ve Göletler',
                    active: showLakes,
                    onTap: onToggleLakes,
                  ),
                ],
              ),

              const Divider(height: 28),

              // ── Sıfırla ──
              Row(
                children: [
                  _outlineBtn(
                    label: 'Sıfırla',
                    active: false,
                    onTap: onReset,
                    color: Colors.grey,
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _sectionTitle(String text) {
    return Text(
      text,
      style: const TextStyle(
        fontWeight: FontWeight.w700,
        fontSize: 13,
        color: AppTheme.brandRed,
      ),
    );
  }

  Widget _outlineBtn({
    required String label,
    required bool active,
    required VoidCallback onTap,
    Color? color,
  }) {
    final c = color ?? AppTheme.brandRed;
    return OutlinedButton(
      onPressed: onTap,
      style: OutlinedButton.styleFrom(
        foregroundColor: active ? Colors.white : c,
        backgroundColor: active ? c.withValues(alpha: 0.85) : Colors.white,
        side: BorderSide(color: c.withValues(alpha: 0.5)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
      ),
      child: Text(label),
    );
  }

  Widget _primaryBtn({required String label, required VoidCallback onTap}) {
    return ElevatedButton(
      onPressed: onTap,
      style: ElevatedButton.styleFrom(
        backgroundColor: AppTheme.brandRed,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
      ),
      child: Text(label),
    );
  }
}
