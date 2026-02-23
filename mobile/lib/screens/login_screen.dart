import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:provider/provider.dart';
import '../config/app_theme.dart';
import '../services/auth_service.dart';
import 'welcome_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with SingleTickerProviderStateMixin {
  bool _showModal = false;
  bool _isLogin = true; // true = login, false = signup
  String _userType = 'user'; // 'user' or 'admin'
  String _language = 'tr';

  // Login controllers
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();

  // Signup controllers
  final _signupFullnameCtrl = TextEditingController();
  final _signupEmailCtrl = TextEditingController();
  final _signupUsernameCtrl = TextEditingController();
  final _signupPasswordCtrl = TextEditingController();
  final _signupConfirmCtrl = TextEditingController();
  bool _termsAccepted = false;

  String? _errorMessage;

  void _showError(String msg) {
    setState(() => _errorMessage = msg);
    Future.delayed(const Duration(seconds: 4), () {
      if (mounted) setState(() => _errorMessage = null);
    });
  }

  Future<void> _handleLogin() async {
    final username = _usernameCtrl.text.trim();
    final password = _passwordCtrl.text.trim();
    if (username.isEmpty || password.isEmpty) {
      _showError('Lütfen tüm alanları doldurunuz');
      return;
    }

    final auth = context.read<AuthService>();
    await auth.login(username, password, role: _userType);

    if (auth.isLoggedIn && mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const WelcomeScreen()),
      );
    }
  }

  Future<void> _handleSignup() async {
    final fullname = _signupFullnameCtrl.text.trim();
    final email = _signupEmailCtrl.text.trim();
    final username = _signupUsernameCtrl.text.trim();
    final password = _signupPasswordCtrl.text.trim();
    final confirm = _signupConfirmCtrl.text.trim();

    if (fullname.isEmpty ||
        email.isEmpty ||
        username.isEmpty ||
        password.isEmpty ||
        confirm.isEmpty) {
      _showError('Lütfen tüm alanları doldurunuz');
      return;
    }
    if (password != confirm) {
      _showError('Şifreler eşleşmiyor');
      return;
    }
    if (password.length < 6) {
      _showError('Şifre en az 6 karakter olmalıdır');
      return;
    }
    if (!_termsAccepted) {
      _showError('Lütfen şartları ve koşulları kabul ediniz');
      return;
    }

    final auth = context.read<AuthService>();
    await auth.register(
      username,
      password,
      role: 'user',
      fullname: fullname,
      email: email,
    );

    if (auth.isLoggedIn && mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const WelcomeScreen()),
      );
    }
  }

  @override
  void dispose() {
    _usernameCtrl.dispose();
    _passwordCtrl.dispose();
    _signupFullnameCtrl.dispose();
    _signupEmailCtrl.dispose();
    _signupUsernameCtrl.dispose();
    _signupPasswordCtrl.dispose();
    _signupConfirmCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          // Background
          SizedBox.expand(
            child: SvgPicture.asset(
              'assets/login-bg.svg',
              fit: BoxFit.cover,
              placeholderBuilder: (_) => Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      AppTheme.darkGreen,
                      Color(0xFF1A3A0A),
                      Color(0xFF0A1F05),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // KORU title – shown when modal is closed
          if (!_showModal)
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              child: SafeArea(
                child: Padding(
                  padding: const EdgeInsets.only(top: 32),
                  child: Column(
                    children: [
                      const Text(
                        'KORU',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 52,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                          letterSpacing: 6,
                          shadows: [
                            Shadow(
                              color: Colors.black54,
                              blurRadius: 16,
                              offset: Offset(0, 4),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'YANGINDA KORUNMA PLATFORMU',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w400,
                          color: Colors.white.withValues(alpha: 0.75),
                          letterSpacing: 3,
                          shadows: [
                            const Shadow(color: Colors.black54, blurRadius: 8),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),

          // Landing button
          if (!_showModal)
            Positioned(
              bottom: 120,
              left: 0,
              right: 0,
              child: Center(
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.darkGreen,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 36,
                      vertical: 14,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    elevation: 8,
                  ),
                  onPressed: () => setState(() => _showModal = true),
                  child: const Text(
                    'GİRİŞ YAP',
                    style: TextStyle(
                      fontWeight: FontWeight.w400,
                      fontSize: 13,
                      letterSpacing: 1.5,
                    ),
                  ),
                ),
              ),
            ),

          // Language selector
          Positioned(
            bottom: 12,
            left: 12,
            child: Container(
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.25),
                borderRadius: BorderRadius.circular(6),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _langBtn('TR', 'tr'),
                  const SizedBox(width: 4),
                  _langBtn('ENG', 'en'),
                ],
              ),
            ),
          ),

          // Modal
          if (_showModal) _buildModal(),
        ],
      ),
    );
  }

  Widget _langBtn(String label, String code) {
    final active = _language == code;
    return GestureDetector(
      onTap: () => setState(() => _language = code),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: active ? AppTheme.lightGreen : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: active
                ? AppTheme.lightGreen
                : Colors.white.withValues(alpha: 0.2),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 9,
            fontWeight: FontWeight.w400,
            color: active ? Colors.white : Colors.white.withValues(alpha: 0.6),
            letterSpacing: 0.3,
          ),
        ),
      ),
    );
  }

  Widget _buildModal() {
    final auth = context.watch<AuthService>();

    return GestureDetector(
      onTap: () => setState(() {
        _showModal = false;
        _errorMessage = null;
      }),
      child: Container(
        color: Colors.black.withValues(alpha: 0.5),
        child: Center(
          child: GestureDetector(
            onTap: () {}, // prevent close on tap inside
            child: SingleChildScrollView(
              child: Container(
                margin: const EdgeInsets.all(20),
                padding: const EdgeInsets.all(28),
                constraints: const BoxConstraints(maxWidth: 450),
                decoration: BoxDecoration(
                  color: AppTheme.darkGreen,
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.4),
                      blurRadius: 50,
                      offset: const Offset(0, 25),
                    ),
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Header
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'KORU',
                          style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.w800,
                            color: Colors.white,
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close, color: Colors.white),
                          onPressed: () => setState(() {
                            _showModal = false;
                            _errorMessage = null;
                          }),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),

                    // Error
                    if (_errorMessage != null)
                      Container(
                        padding: const EdgeInsets.all(12),
                        margin: const EdgeInsets.only(bottom: 16),
                        decoration: BoxDecoration(
                          color: const Color(0xFFFF6B6B).withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(8),
                          border: const Border(
                            left: BorderSide(
                              color: Color(0xFFFF6B6B),
                              width: 4,
                            ),
                          ),
                        ),
                        child: Text(
                          _errorMessage!,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),

                    // Tab toggle
                    Container(
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      padding: const EdgeInsets.all(6),
                      child: Row(
                        children: [
                          _tabBtn('GİRİŞ YAP', true),
                          const SizedBox(width: 12),
                          _tabBtn('KAYIT OL', false),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),

                    // User type selector (login only)
                    if (_isLogin) ...[
                      Row(
                        children: [
                          _userTypeBtn('👤 Kullanıcı', 'user'),
                          const SizedBox(width: 12),
                          _userTypeBtn('🔐 Admin', 'admin'),
                        ],
                      ),
                      const SizedBox(height: 20),
                    ],

                    // Forms
                    if (_isLogin) _buildLoginForm(auth),
                    if (!_isLogin) _buildSignupForm(auth),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _tabBtn(String label, bool isLoginTab) {
    final active = _isLogin == isLoginTab;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() {
          _isLogin = isLoginTab;
          _errorMessage = null;
        }),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: active ? AppTheme.lightGreen : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            boxShadow: active
                ? [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.2),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ]
                : null,
          ),
          alignment: Alignment.center,
          child: Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w400,
              letterSpacing: 0.8,
              color: active
                  ? Colors.white
                  : Colors.white.withValues(alpha: 0.6),
            ),
          ),
        ),
      ),
    );
  }

  Widget _userTypeBtn(String label, String type) {
    final active = _userType == type;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _userType = type),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: active
                ? AppTheme.lightGreen
                : Colors.white.withValues(alpha: 0.05),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: active
                  ? AppTheme.lightGreen
                  : Colors.white.withValues(alpha: 0.2),
              width: 2,
            ),
          ),
          alignment: Alignment.center,
          child: Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: active
                  ? Colors.white
                  : Colors.white.withValues(alpha: 0.7),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildLoginForm(AuthService auth) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _label('Kullanıcı Adı'),
        _input(_usernameCtrl, 'Kullanıcı adınızı girin'),
        const SizedBox(height: 16),
        _label('Şifre'),
        _input(_passwordCtrl, 'Şifrenizi girin', obscure: true),
        const SizedBox(height: 20),
        ElevatedButton(
          onPressed: auth.loading ? null : _handleLogin,
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.lightGreen,
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
          child: auth.loading
              ? const SizedBox(
                  height: 20,
                  width: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              : const Text(
                  'GİRİŞ YAP',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                    letterSpacing: 0.5,
                    color: Colors.white,
                  ),
                ),
        ),
        const SizedBox(height: 16),
        Text(
          'Demo: Herhangi bir kullanıcı adı ve şifre ile giriş yapabilirsiniz',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 11,
            color: Colors.white.withValues(alpha: 0.6),
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(4),
            border: const Border(
              left: BorderSide(color: AppTheme.lightGreen, width: 4),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '📋 Test Hesapları:',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: Colors.white,
                  fontSize: 11,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Kullanıcı: user1 / password123',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.7),
                  fontSize: 11,
                ),
              ),
              Text(
                'Admin: admin / admin123',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.7),
                  fontSize: 11,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSignupForm(AuthService auth) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _label('Ad Soyad'),
        _input(_signupFullnameCtrl, 'Ad ve soyadınızı girin'),
        const SizedBox(height: 14),
        _label('E-posta'),
        _input(
          _signupEmailCtrl,
          'E-posta adresinizi girin',
          keyboardType: TextInputType.emailAddress,
        ),
        const SizedBox(height: 14),
        _label('Kullanıcı Adı'),
        _input(_signupUsernameCtrl, 'Bir kullanıcı adı seçin'),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _label('Şifre'),
                  _input(_signupPasswordCtrl, 'Şifre', obscure: true),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _label('Şifre Tekrarı'),
                  _input(_signupConfirmCtrl, 'Tekrar', obscure: true),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Checkbox(
              value: _termsAccepted,
              onChanged: (v) => setState(() => _termsAccepted = v ?? false),
              activeColor: AppTheme.lightGreen,
            ),
            Expanded(
              child: Text(
                'Şartları ve koşulları kabul ediyorum',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.white.withValues(alpha: 0.7),
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        ElevatedButton(
          onPressed: auth.loading ? null : _handleSignup,
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.lightGreen,
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
          child: auth.loading
              ? const SizedBox(
                  height: 20,
                  width: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              : const Text(
                  'KAYIT OL',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                    color: Colors.white,
                  ),
                ),
        ),
      ],
    );
  }

  Widget _label(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        text.toUpperCase(),
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: Colors.white.withValues(alpha: 0.8),
          letterSpacing: 0.3,
        ),
      ),
    );
  }

  Widget _input(
    TextEditingController ctrl,
    String hint, {
    bool obscure = false,
    TextInputType keyboardType = TextInputType.text,
  }) {
    return TextField(
      controller: ctrl,
      obscureText: obscure,
      keyboardType: keyboardType,
      style: const TextStyle(color: Colors.white, fontSize: 14),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.4)),
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.08),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.15)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(
            color: Colors.white.withValues(alpha: 0.15),
            width: 1.5,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: AppTheme.lightGreen, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 14,
          vertical: 12,
        ),
      ),
    );
  }
}
