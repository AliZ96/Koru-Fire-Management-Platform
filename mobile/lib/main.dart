import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'config/app_theme.dart';
import 'services/api_service.dart';
import 'services/auth_service.dart';
import 'services/map_data_service.dart';
import 'screens/login_screen.dart';
import 'screens/map_screen.dart';

import 'package:firebase_core/firebase_core.dart';
import 'config/firebase_options.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
  } catch (e) {
    // Firebase app might already be initialized
    debugPrint('Firebase init: $e');
  }

  final apiService = ApiService();
  final authService = AuthService(apiService);
  final mapDataService = MapDataService(apiService);

  runApp(
    MultiProvider(
      providers: [
        Provider<ApiService>.value(value: apiService),
        ChangeNotifierProvider<AuthService>.value(value: authService),
        ChangeNotifierProvider<MapDataService>.value(value: mapDataService),
      ],
      child: const KoruApp(),
    ),
  );
}

class KoruApp extends StatelessWidget {
  const KoruApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'KORU',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: const _SplashGate(),
    );
  }
}

/// Checks if user has a saved session and routes accordingly.
class _SplashGate extends StatefulWidget {
  const _SplashGate();

  @override
  State<_SplashGate> createState() => _SplashGateState();
}

class _SplashGateState extends State<_SplashGate> {
  bool _ready = false;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    try {
      final auth = Provider.of<AuthService>(context, listen: false);
      await auth.tryRestoreSession();
      if (mounted) setState(() => _ready = true);
    } catch (e) {
      debugPrint('Session restore error: $e');
      if (mounted) setState(() => _ready = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_ready) {
      return Scaffold(
        backgroundColor: AppTheme.darkGreen,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'KORU',
                style: TextStyle(
                  fontSize: 48,
                  fontWeight: FontWeight.w800,
                  color: Colors.white,
                  letterSpacing: 3,
                ),
              ),
              Container(height: 24),
              CircularProgressIndicator(color: Colors.white),
            ],
          ),
        ),
      );
    }

    final auth = context.watch<AuthService>();
    if (auth.isLoggedIn) {
      return const MapScreen();
    }
    return const LoginScreen();
  }
}
