/// Backend API configuration.
/// Change [baseUrl] to your server's address.
class ApiConfig {
  // For Android emulator use 10.0.2.2 instead of localhost
  // For physical device use your computer's local IP (e.g. 192.168.1.x)
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8000',
  );

  // Auth endpoints
  static const String loginUser = '/auth/user/login';
  static const String registerUser = '/auth/user/register';
  static const String loginFirefighter = '/auth/firefighter/login';
  static const String registerFirefighter = '/auth/firefighter/register';
  static const String me = '/auth/me';

  // Data endpoints
  static const String firms = '/api/firms';
  static const String fires = '/api/fires';
  static const String wind = '/api/wind';
  static const String dams = '/api/dams';
  static const String waterSources = '/api/water_sources';
  static const String waterTanks = '/api/water_tanks';

  // Fire risk ML endpoints
  static const String fireRiskPoints = '/api/fire-risk/points';
  static const String fireRiskStats = '/api/fire-risk/statistics';
  static const String fireRiskHeatmap = '/api/fire-risk/heatmap-data';

  // Accessibility endpoints
  static const String accessibilityGroundMap = '/api/accessibility/ground/map';
  static const String accessibilityIntegratedMap =
      '/api/accessibility/integrated/map';
  static const String accessibilityLevels = '/api/accessibility/levels';

  // Health
  static const String healthDb = '/health/db';

  // UI copy sync endpoints
  static const String mobileUiLogin = '/api/mobile-ui/login';
  static const String mobileUiWelcome = '/api/mobile-ui/welcome';
  static const String mobileUiMap = '/api/mobile-ui/map';
}
