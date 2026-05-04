import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';

const _kTimeout = Duration(seconds: 6);

/// Central HTTP service for all backend API calls.
class ApiService {
  final String baseUrl;
  String? _token;

  ApiService({String? baseUrl}) : baseUrl = baseUrl ?? ApiConfig.baseUrl;

  void setToken(String? token) => _token = token;

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    if (_token != null) 'Authorization': 'Bearer $_token',
  };

  // ─── Auth ─────────────────────────────────────────────

  Future<Map<String, dynamic>> login(
    String username,
    String password, {
    String role = 'user',
  }) async {
    final endpoint = role == 'firefighter'
        ? ApiConfig.loginFirefighter
        : ApiConfig.loginUser;
    final res = await http
        .post(
          Uri.parse('$baseUrl$endpoint'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'username': username, 'password': password}),
        )
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<Map<String, dynamic>> register(
    String username,
    String password,
    String role,
  ) async {
    final endpoint = role == 'firefighter'
        ? ApiConfig.registerFirefighter
        : ApiConfig.registerUser;
    final res = await http
        .post(
          Uri.parse('$baseUrl$endpoint'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'username': username,
            'password': password,
            'role': role,
          }),
        )
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<Map<String, dynamic>> getMe() async {
    final res = await http
        .get(Uri.parse('$baseUrl${ApiConfig.me}'), headers: _headers)
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<Map<String, dynamic>> exchangeFirebaseToken(
    String firebaseToken,
  ) async {
    final res = await http
        .post(
          Uri.parse('$baseUrl/auth/firebase-token'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'firebase_token': firebaseToken}),
        )
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<Map<String, dynamic>> syncFirebaseUser(
    String firebaseUid,
    String displayName,
    String role,
  ) async {
    final res = await http
        .post(
          Uri.parse('$baseUrl/auth/user/sync'),
          headers: _headers,
          body: jsonEncode({
            'firebase_uid': firebaseUid,
            'display_name': displayName,
            'role': role,
          }),
        )
        .timeout(_kTimeout);
    return _decode(res);
  }

  // ─── FIRMS / Fires ────────────────────────────────────

  Future<Map<String, dynamic>> getFires({int dayRange = 1}) async {
    final res = await http
        .get(
          Uri.parse('$baseUrl${ApiConfig.firms}?day_range=$dayRange'),
          headers: _headers,
        )
        .timeout(_kTimeout);
    return _decode(res);
  }

  // ─── Wind ─────────────────────────────────────────────

  Future<Map<String, dynamic>> getWind(double lat, double lon) async {
    final res = await http
        .get(
          Uri.parse('$baseUrl${ApiConfig.wind}?lat=$lat&lon=$lon'),
          headers: _headers,
        )
        .timeout(_kTimeout);
    return _decode(res);
  }

  // ─── Fire Risk ML ─────────────────────────────────────

  Future<Map<String, dynamic>> getFireRiskPoints({
    String? riskClass,
    int limit = 50000,
  }) async {
    String url = '$baseUrl${ApiConfig.fireRiskPoints}?limit=$limit';
    if (riskClass != null) url += '&risk_class=$riskClass';
    final res = await http
        .get(Uri.parse(url), headers: _headers)
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<Map<String, dynamic>> getFireRiskStatistics() async {
    final res = await http
        .get(Uri.parse('$baseUrl${ApiConfig.fireRiskStats}'), headers: _headers)
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<Map<String, dynamic>> getFireRiskHeatmap({
    double cellSize = 0.05,
  }) async {
    final res = await http
        .get(
          Uri.parse('$baseUrl${ApiConfig.fireRiskHeatmap}?cell_size=$cellSize'),
          headers: _headers,
        )
        .timeout(_kTimeout);
    return _decode(res);
  }

  // ─── Accessibility ────────────────────────────────────

  Future<Map<String, dynamic>> getAccessibilityMap({
    String? accessClass,
    double? minLon,
    double? minLat,
    double? maxLon,
    double? maxLat,
  }) async {
    String url = '$baseUrl${ApiConfig.accessibilityGroundMap}';
    final params = <String>[];

    if (accessClass != null) params.add('access_class=$accessClass');
    if (minLon != null) params.add('min_lon=$minLon');
    if (minLat != null) params.add('min_lat=$minLat');
    if (maxLon != null) params.add('max_lon=$maxLon');
    if (maxLat != null) params.add('max_lat=$maxLat');

    if (params.isNotEmpty) {
      url += '?${params.join('&')}';
    }

    final res = await http
        .get(Uri.parse(url), headers: _headers)
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<Map<String, dynamic>> getAccessibilityIntegratedMap({
    String? riskClass,
    String? accessClass,
    double? minLon,
    double? minLat,
    double? maxLon,
    double? maxLat,
  }) async {
    String url = '$baseUrl${ApiConfig.accessibilityIntegratedMap}';
    final params = <String>[];

    if (riskClass != null) params.add('risk_class=$riskClass');
    if (accessClass != null) params.add('access_class=$accessClass');
    if (minLon != null) params.add('min_lon=$minLon');
    if (minLat != null) params.add('min_lat=$minLat');
    if (maxLon != null) params.add('max_lon=$maxLon');
    if (maxLat != null) params.add('max_lat=$maxLat');

    if (params.isNotEmpty) {
      url += '?${params.join('&')}';
    }

    final res = await http
        .get(Uri.parse(url), headers: _headers)
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<Map<String, dynamic>> getAccessibilityLevels() async {
    final res = await http
        .get(
          Uri.parse('$baseUrl${ApiConfig.accessibilityLevels}'),
          headers: _headers,
        )
        .timeout(_kTimeout);
    return _decode(res);
  }

  // ─── Health ───────────────────────────────────────────

  Future<Map<String, dynamic>> healthCheck() async {
    final res = await http
        .get(Uri.parse('$baseUrl${ApiConfig.healthDb}'), headers: _headers)
        .timeout(_kTimeout);
    return _decode(res);
  }

  // ─── Mobile UI Copy Sync ──────────────────────────────

  Future<Map<String, dynamic>> getLoginUiCopy() async {
    final res = await http
        .get(Uri.parse('$baseUrl${ApiConfig.mobileUiLogin}'), headers: _headers)
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<Map<String, dynamic>> getWelcomeUiCopy() async {
    final res = await http
        .get(
          Uri.parse('$baseUrl${ApiConfig.mobileUiWelcome}'),
          headers: _headers,
        )
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<Map<String, dynamic>> getMapUiCopy() async {
    final res = await http
        .get(Uri.parse('$baseUrl${ApiConfig.mobileUiMap}'), headers: _headers)
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<Map<String, dynamic>> getIzmirBoundaryGeoJson() async {
    final res = await http
        .get(Uri.parse('$baseUrl/static/data/izmir.geojson'), headers: _headers)
        .timeout(_kTimeout);
    return _decode(res);
  }

  // ─── Fire Spread ──────────────────────────────────────

  Future<List<dynamic>> getSpreadScenarios() async {
    final res = await http
        .get(Uri.parse('$baseUrl/api/fire-spread/scenarios'), headers: _headers)
        .timeout(_kTimeout);
    final body = jsonDecode(res.body);
    return body as List<dynamic>;
  }

  Future<Map<String, dynamic>> createSpreadScenario({
    required String name,
    required double lat,
    required double lon,
  }) async {
    final res = await http
        .post(
          Uri.parse('$baseUrl/api/fire-spread/scenarios'),
          headers: _headers,
          body: jsonEncode({'name': name, 'lat': lat, 'lon': lon}),
        )
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<Map<String, dynamic>> getCurrentSpread(dynamic scenarioId) async {
    final res = await http
        .get(
          Uri.parse('$baseUrl/api/fire-spread/scenarios/$scenarioId/current'),
          headers: _headers,
        )
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<Map<String, dynamic>> stopSpreadScenario(dynamic scenarioId) async {
    final res = await http
        .patch(
          Uri.parse('$baseUrl/api/fire-spread/scenarios/$scenarioId/stop'),
          headers: _headers,
        )
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<Map<String, dynamic>> deleteAllSpreadScenarios() async {
    final res = await http
        .delete(
          Uri.parse('$baseUrl/api/fire-spread/scenarios'),
          headers: _headers,
        )
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<Map<String, dynamic>> getSpreadEta({
    required dynamic scenarioId,
    required double lat,
    required double lon,
  }) async {
    final res = await http
        .get(
          Uri.parse(
            '$baseUrl/api/fire-spread/scenarios/$scenarioId/eta?lat=$lat&lon=$lon',
          ),
          headers: _headers,
        )
        .timeout(_kTimeout);
    return _decode(res);
  }

  Future<void> saveMySpreadLocation(double lat, double lon) async {
    await http
        .post(
          Uri.parse('$baseUrl/api/fire-spread/my-location'),
          headers: _headers,
          body: jsonEncode({'lat': lat, 'lon': lon}),
        )
        .timeout(_kTimeout);
  }

  String getSpreadWsUrl(dynamic scenarioId) {
    final wsBase = baseUrl
        .replaceFirst('https://', 'wss://')
        .replaceFirst('http://', 'ws://');
    return '$wsBase/api/fire-spread/ws/$scenarioId';
  }

  // ─── Helpers ──────────────────────────────────────────

  Map<String, dynamic> _decode(http.Response res) {
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return jsonDecode(res.body) as Map<String, dynamic>;
    }
    // Try to parse error body
    try {
      final body = jsonDecode(res.body);
      throw ApiException(
        statusCode: res.statusCode,
        message: (body is Map ? body['detail']?.toString() : null) ?? res.body,
      );
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(statusCode: res.statusCode, message: res.body);
    }
  }
}

class ApiException implements Exception {
  final int statusCode;
  final String message;
  ApiException({required this.statusCode, required this.message});

  @override
  String toString() => 'ApiException($statusCode): $message';
}
