import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../config/app_theme.dart';
import '../services/auth_service.dart';
import 'login_screen.dart';
import 'map_screen.dart';

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final username = auth.user?.username ?? 'Kullanıcı';

    return Scaffold(
      body: Stack(
        children: [
          // Background gradient (replaces video on mobile)
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0xFF0A1F05),
                  Color(0xFF1A3A0A),
                  AppTheme.darkGreen,
                  Color(0xFF3A5A2A),
                ],
              ),
            ),
          ),

          // Decorative overlay
          Container(
            decoration: BoxDecoration(
              gradient: RadialGradient(
                center: Alignment.center,
                radius: 1.2,
                colors: [
                  Colors.white.withValues(alpha: 0.02),
                  Colors.transparent,
                ],
              ),
            ),
          ),

          // Content
          SafeArea(
            child: Column(
              children: [
                // User bar at top
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 8,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      Text(
                        username,
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.8),
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(width: 8),
                      PopupMenuButton<String>(
                        icon: Icon(
                          Icons.account_circle,
                          color: Colors.white.withValues(alpha: 0.8),
                          size: 28,
                        ),
                        onSelected: (value) async {
                          if (value == 'logout') {
                            await auth.logout();
                            if (context.mounted) {
                              Navigator.pushReplacement(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => const LoginScreen(),
                                ),
                              );
                            }
                          } else if (value == 'profile') {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(
                                  'Profil: $username (${auth.user?.role ?? "user"})',
                                ),
                                backgroundColor: AppTheme.darkGreen,
                              ),
                            );
                          }
                        },
                        itemBuilder: (_) => [
                          const PopupMenuItem(
                            value: 'profile',
                            child: Row(
                              children: [
                                Icon(Icons.person, size: 18),
                                SizedBox(width: 8),
                                Text('Profil'),
                              ],
                            ),
                          ),
                          const PopupMenuItem(
                            value: 'logout',
                            child: Row(
                              children: [
                                Icon(Icons.logout, size: 18),
                                SizedBox(width: 8),
                                Text('Oturum Kapat'),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),

                const Spacer(),

                // Title
                const Text(
                  'KORU',
                  style: TextStyle(
                    fontSize: 60,
                    fontWeight: FontWeight.w800,
                    color: Colors.white,
                    letterSpacing: 3,
                    shadows: [
                      Shadow(
                        color: Colors.black45,
                        blurRadius: 20,
                        offset: Offset(0, 4),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 50),

                // Navigation buttons
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: Column(
                    children: [
                      _WelcomeButton(
                        label: 'Canlı Yangın ve\nRisk Haritası',
                        icon: Icons.local_fire_department,
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => const MapScreen(),
                            ),
                          );
                        },
                      ),
                      const SizedBox(height: 20),
                      _WelcomeButton(
                        label: 'İtfaiye Nerede?',
                        icon: Icons.fire_truck,
                        onTap: () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text(
                                'İtfaiye istasyonları özelliği yakında açılacak',
                              ),
                            ),
                          );
                        },
                      ),
                    ],
                  ),
                ),

                const Spacer(),
                const SizedBox(height: 40),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _WelcomeButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;

  const _WelcomeButton({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 36, horizontal: 28),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: Colors.white.withValues(alpha: 0.3),
              width: 2,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.2),
                blurRadius: 32,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: Colors.white, size: 32),
              const SizedBox(width: 16),
              Flexible(
                child: Text(
                  label,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
