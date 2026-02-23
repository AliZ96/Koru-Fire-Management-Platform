import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/user.dart';
import 'api_service.dart';

/// Manages authentication state. Used as a ChangeNotifier with Provider.
class AuthService extends ChangeNotifier {
  final ApiService _api;
  User? _user;
  bool _loading = false;

  AuthService(this._api);

  User? get user => _user;
  bool get isLoggedIn => _user != null;
  bool get loading => _loading;

  /// Attempt to restore session from SharedPreferences.
  Future<void> tryRestoreSession() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token');
    final username = prefs.getString('username');
    final role = prefs.getString('user_role');
    if (token != null && username != null) {
      _api.setToken(token);
      _user = User(
        username: username,
        role: role ?? 'user',
        accessToken: token,
      );
      notifyListeners();
    }
  }

  /// Login with username/password.
  Future<void> login(
    String username,
    String password, {
    String role = 'user',
  }) async {
    _loading = true;
    notifyListeners();
    try {
      final data = await _api.login(username, password, role: role);
      final token = data['access_token'] as String?;
      if (token != null) {
        _api.setToken(token);
        _user = User(username: username, role: role, accessToken: token);
        // Persist
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('access_token', token);
        await prefs.setString('username', username);
        await prefs.setString('user_role', role);
      } else {
        // Demo mode – accept any login
        _user = User(username: username, role: role);
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('username', username);
        await prefs.setString('user_role', role);
      }
    } on ApiException {
      // If server is unreachable or returns error, allow demo login
      _user = User(username: username, role: role);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('username', username);
      await prefs.setString('user_role', role);
    } catch (_) {
      // Fallback demo login
      _user = User(username: username, role: role);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('username', username);
      await prefs.setString('user_role', role);
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  /// Register a new user.
  Future<void> register(
    String username,
    String password, {
    String role = 'user',
    String? fullname,
    String? email,
  }) async {
    _loading = true;
    notifyListeners();
    try {
      final data = await _api.register(username, password, role);
      final token = data['access_token'] as String?;
      _api.setToken(token);
      _user = User(
        username: username,
        role: role,
        fullname: fullname,
        email: email,
        accessToken: token,
      );
      final prefs = await SharedPreferences.getInstance();
      if (token != null) await prefs.setString('access_token', token);
      await prefs.setString('username', username);
      await prefs.setString('user_role', role);
    } on ApiException {
      // Demo mode
      _user = User(
        username: username,
        role: role,
        fullname: fullname,
        email: email,
      );
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('username', username);
      await prefs.setString('user_role', role);
    } catch (_) {
      _user = User(username: username, role: role);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('username', username);
      await prefs.setString('user_role', role);
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  /// Logout and clear session.
  Future<void> logout() async {
    _user = null;
    _api.setToken(null);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('username');
    await prefs.remove('user_role');
    notifyListeners();
  }
}
