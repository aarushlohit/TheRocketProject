import 'package:flutter/material.dart';

/// Unified app theme matching home page design
class AppTheme {
  AppTheme._();

  // ============ COLORS ============
  
  static const Color background = Color(0xFFF7F8FA);
  
  /// Dark navy for text
  static const Color textPrimary = Color(0xFF1A1A2E);
  static const Color textSecondary = Color(0xFF4A4A5E);
  static const Color textMuted = Color(0xFF8A8A9E);
  
  static const Color primary = Color(0xFF005FCC);
  static const Color primaryLight = Color(0xFF4C9AFF);
  static const Color primaryDark = Color(0xFF003F8C);
  
  /// Success/Error colors
  static const Color success = Color(0xFF4CAF50);
  static const Color error = Color(0xFFE53935);
  static const Color warning = Color(0xFFFF9800);
  
  static const Color cardVoice = Color(0xFFFFFFFF);
  static const Color cardDrawing = Color(0xFFFFF7D6);
  static const Color cardBraille = Color(0xFFE7F7EF);
  static const Color cardSettings = Color(0xFFEAF1FF);
  
  /// Disability card colors
  static const Color cardVisual = Color(0xFFE8F5E9);
  static const Color cardHearing = Color(0xFFFFF3E0);
  static const Color cardMotor = Color(0xFFE3F2FD);
  static const Color cardCognitive = Color(0xFFFCE4EC);

  // ============ TYPOGRAPHY ============
  
  static const TextStyle headingLarge = TextStyle(
    fontSize: 32,
    fontWeight: FontWeight.w700,
    color: textPrimary,
    height: 1.2,
  );
  
  static const TextStyle headingMedium = TextStyle(
    fontSize: 24,
    fontWeight: FontWeight.w700,
    color: textPrimary,
    height: 1.3,
  );
  
  static const TextStyle headingSmall = TextStyle(
    fontSize: 20,
    fontWeight: FontWeight.w600,
    color: textPrimary,
    height: 1.3,
  );
  
  static const TextStyle bodyLarge = TextStyle(
    fontSize: 18,
    fontWeight: FontWeight.w500,
    color: textPrimary,
    height: 1.4,
  );
  
  static const TextStyle bodyMedium = TextStyle(
    fontSize: 16,
    fontWeight: FontWeight.w400,
    color: textSecondary,
    height: 1.5,
  );
  
  static const TextStyle bodySmall = TextStyle(
    fontSize: 14,
    fontWeight: FontWeight.w400,
    color: textMuted,
    height: 1.5,
  );
  
  static const TextStyle buttonText = TextStyle(
    fontSize: 18,
    fontWeight: FontWeight.w600,
    color: Colors.white,
    letterSpacing: 0.5,
  );

  // ============ DECORATIONS ============
  
  static BoxDecoration cardDecoration({
    required Color backgroundColor,
    bool isSelected = false,
    bool hasShadow = true,
  }) {
    return BoxDecoration(
      color: isSelected ? backgroundColor.withValues(alpha: 0.95) : backgroundColor,
      borderRadius: BorderRadius.circular(8),
      border: Border.all(
        color: isSelected ? primary : Colors.black12,
        width: isSelected ? 2.5 : 1.0,
      ),
      boxShadow: hasShadow
          ? [
              BoxShadow(
                color: Colors.black.withValues(alpha: isSelected ? 0.08 : 0.05),
                blurRadius: isSelected ? 20 : 12,
                offset: const Offset(0, 6),
              ),
            ]
          : null,
    );
  }
  
  static BoxDecoration primaryButtonDecoration = BoxDecoration(
    color: primary,
    borderRadius: BorderRadius.circular(8),
    boxShadow: [
      BoxShadow(
        color: primary.withValues(alpha: 0.35),
        blurRadius: 16,
        offset: const Offset(0, 6),
      ),
    ],
  );
  
  static BoxDecoration secondaryButtonDecoration = BoxDecoration(
    color: Colors.white,
    borderRadius: BorderRadius.circular(8),
    border: Border.all(color: primary, width: 2),
  );

  // ============ SPACING ============
  
  static const double spacingXS = 4;
  static const double spacingS = 8;
  static const double spacingM = 16;
  static const double spacingL = 24;
  static const double spacingXL = 32;
  static const double spacingXXL = 48;

  // ============ THEME DATA ============
  
  static ThemeData get themeData => ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: primary,
      brightness: Brightness.light,
    ),
    scaffoldBackgroundColor: background,
    appBarTheme: const AppBarTheme(
      backgroundColor: background,
      foregroundColor: textPrimary,
      elevation: 0,
    ),
  );
}
