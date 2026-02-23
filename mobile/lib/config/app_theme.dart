import 'package:flutter/material.dart';

class AppTheme {
  // Brand colors (matching web's --brand-blue / dark-red)
  static const Color brandRed = Color(0xFF8B0000);
  static const Color darkGreen = Color(0xFF2D5016);
  static const Color forestGreen = Color(0xFF4A7C3A);
  static const Color lightGreen = Color(0xFF6B9D52);

  // Risk colors
  static const Color riskHigh = Color(0xFF8B0000);
  static const Color riskMedium = Color(0xFFE74C3C);
  static const Color riskLow = Color(0xFFF39C12);
  static const Color riskSafe = Color(0xFF2ECC71);

  // Water layer colors
  static const Color waterReservoir = Color(0xFFC41E3A);
  static const Color waterSource = Color(0xFF0277BD);
  static const Color waterTank = Color(0xFF64B5F6);
  static const Color lake = Color(0xFF1565C0);

  // Fire confidence colors
  static Color fireConfidenceColor(String confidence) {
    switch (confidence.toLowerCase()) {
      case 'h':
        return const Color(0xFFD32F2F);
      case 'n':
        return const Color(0xFFF57C00);
      default:
        return const Color(0xFF1976D2);
    }
  }

  static ThemeData get lightTheme => ThemeData(
    primaryColor: brandRed,
    colorScheme: ColorScheme.fromSeed(
      seedColor: brandRed,
      primary: brandRed,
      secondary: forestGreen,
      brightness: Brightness.light,
    ),
    fontFamily: 'Montserrat',
    appBarTheme: const AppBarTheme(
      backgroundColor: brandRed,
      foregroundColor: Colors.white,
      elevation: 2,
      centerTitle: true,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: lightGreen,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: brandRed,
        side: const BorderSide(color: brandRed),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white.withValues(alpha: 0.08),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.15)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.15)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: lightGreen, width: 2),
      ),
    ),
  );

  static ThemeData get darkLoginTheme => ThemeData(
    brightness: Brightness.dark,
    primaryColor: darkGreen,
    scaffoldBackgroundColor: darkGreen,
    colorScheme: ColorScheme.fromSeed(
      seedColor: darkGreen,
      brightness: Brightness.dark,
    ),
    fontFamily: 'Montserrat',
  );
}
