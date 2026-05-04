import 'package:flutter/material.dart';
import '../config/app_theme.dart';

/// Bottom sheet control panel for the map — mirrors the web panel.
class MapControlPanel extends StatelessWidget {
  final bool hasActiveSpread;

  final VoidCallback onShowSpreadScenario;
  final VoidCallback onShowSpreadList;
  final List<dynamic> scenarios;
  final Function(dynamic id, bool isTracking) onToggleTracking;
  final VoidCallback onDeleteAll;
  final dynamic activeScenarioId;
  final String Function(String key, String fallback) tr;

  const MapControlPanel({
    super.key,
    required this.hasActiveSpread,
    required this.onShowSpreadScenario,
    required this.onShowSpreadList,
    required this.scenarios,
    required this.onToggleTracking,
    required this.onDeleteAll,
    required this.activeScenarioId,
    required this.tr,
  });

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.45,
      minChildSize: 0.3,
      maxChildSize: 0.85,
      builder: (context, scrollController) {
        return Container(
          decoration: BoxDecoration(
            color: AppTheme.webBg.withValues(alpha: 0.95),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.5),
                blurRadius: 16,
                offset: const Offset(0, -2),
              ),
            ],
            border: const Border(
              top: BorderSide(color: AppTheme.webBorder, width: 1.5),
            ),
          ),
          child: ListView(
            controller: scrollController,
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
            children: [
              // Handle bar
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 20),
                  decoration: BoxDecoration(
                    color: Colors.white24,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),

              // ── Yangın Yayılım Takibi ──
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  _sectionTitle(
                    tr('section_layers', 'Yangın Yayılım Takibi'),
                    Icons.local_fire_department_rounded,
                  ),
                  if (scenarios.isNotEmpty)
                    IconButton(
                      icon: const Icon(Icons.delete_sweep_rounded, size: 18, color: Colors.redAccent),
                      onPressed: onDeleteAll,
                      tooltip: 'Tümünü Sil',
                    ),
                ],
              ),
              const SizedBox(height: 12),
              
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.03),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.webBorder),
                ),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: _webBtn(
                            label: tr('btn_spread', 'Yayılım Tahmini Başlat'),
                            active: hasActiveSpread,
                            onTap: onShowSpreadScenario,
                            icon: Icons.add_location_alt_rounded,
                          ),
                        ),
                      ],
                    ),
                    if (scenarios.isNotEmpty) ...[
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: 12),
                        child: Divider(color: AppTheme.webBorder, height: 1),
                      ),
                      ConstrainedBox(
                        constraints: const BoxConstraints(maxHeight: 300),
                        child: ListView.separated(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          itemCount: scenarios.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 8),
                          itemBuilder: (context, index) {
                            final s = scenarios[index];
                            final id = s['id'];
                            final isTracking = activeScenarioId == id;
                            return _scenarioItem(s, isTracking);
                          },
                        ),
                      ),
                    ] else
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 20),
                        child: Text(
                          'Henüz senaryo yok. Haritaya tıklayın.',
                          style: TextStyle(color: AppTheme.webText2.withValues(alpha: 0.5), fontSize: 11),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _scenarioItem(dynamic s, bool isTracking) {
    final name = s['name'] ?? 'İsimsiz Senaryo';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: isTracking ? AppTheme.webAccent.withValues(alpha: 0.08) : Colors.white.withValues(alpha: 0.02),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isTracking ? AppTheme.webAccent.withValues(alpha: 0.3) : AppTheme.webBorder,
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  style: TextStyle(
                    color: isTracking ? AppTheme.webAccent : AppTheme.webText,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  'ID: ${s['id']} • ${double.tryParse(s['elapsed_minutes']?.toString() ?? '0')?.toStringAsFixed(0) ?? '0'} dk',
                  style: TextStyle(color: AppTheme.webText2, fontSize: 10),
                ),
              ],
            ),
          ),
          _smallWebBtn(
            label: isTracking ? 'Durdur' : 'Takip Et',
            active: isTracking,
            onTap: () => onToggleTracking(s['id'], isTracking),
          ),
        ],
      ),
    );
  }

  Widget _smallWebBtn({required String label, required bool active, required VoidCallback onTap}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: active ? AppTheme.webAccent : Colors.white.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w800,
            color: active ? AppTheme.webBg : AppTheme.webText,
          ),
        ),
      ),
    );
  }

  Widget _sectionTitle(String text, IconData icon) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(6),
          decoration: BoxDecoration(
            color: AppTheme.webAccent.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            icon,
            size: 16,
            color: AppTheme.webAccent,
          ),
        ),
        const SizedBox(width: 10),
        Text(
          text,
          style: const TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 13,
            color: AppTheme.webText,
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }

  Widget _webBtn({
    required String label,
    required bool active,
    required VoidCallback onTap,
    required IconData icon,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: active 
            ? AppTheme.webAccent.withValues(alpha: 0.15) 
            : Colors.white.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: active 
              ? AppTheme.webAccent 
              : AppTheme.webBorder,
            width: 1.2,
          ),
          boxShadow: active ? [
            BoxShadow(
              color: AppTheme.webAccent.withValues(alpha: 0.2),
              blurRadius: 8,
              offset: const Offset(0, 2),
            )
          ] : null,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 14,
              color: active ? AppTheme.webAccent : AppTheme.webText2,
            ),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: active ? AppTheme.webAccent : AppTheme.webText,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
