import 'package:flutter/material.dart';

/// Palette FASO LOVE — identité propre au produit (ne pas réutiliser le
/// rose « SparkMatch » / #FE3C72 du projet d'origine).
///
/// Inspirée du Burkina Faso : terracotta, doré de la savane, vert profond.
class AppColors {
  // Couleurs principales
  static const Color primary = Color(0xFFC65D3B); // Terracotta
  static const Color primaryDark = Color(0xFF8F3A1F);
  static const Color primaryLight = Color(0xFFE8A08A);

  // Couleurs secondaires
  static const Color secondary = Color(0xFFD9A21B); // Doré savane
  static const Color secondaryDark = Color(0xFFA87B0A);
  static const Color secondaryLight = Color(0xFFF2CE73);

  // Statuts
  static const Color success = Color(0xFF1E7B3C); // Vert Burkina
  static const Color warning = Color(0xFFE0A400);
  static const Color error = Color(0xFFD32F2F);
  static const Color info = Color(0xFF2196F3);

  // Arrière-plans & surfaces
  static const Color background = Color(0xFFFAFAFA);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color onSurface = Color(0xFF212121);

  // Textes
  static const Color textPrimary = Color(0xFF212121);
  static const Color textSecondary = Color(0xFF757575);
  static const Color textDisabled = Color(0xFF9E9E9E);
  static const Color textOnPrimary = Color(0xFFFFFFFF);
  static const Color textOnSecondary = Color(0xFF212121);

  // Bordures
  static const Color borderLight = Color(0xFFE0E0E0);
  static const Color borderDark = Color(0xFFBDBDBD);

  // Divers
  static const Color disabled = Color(0xFFE0E0E0);
  static const Color divider = Color(0xFFEEEEEE);
  static const Color shadow = Color(0x1A000000);

  // Actions de découverte (swipe)
  static const Color like = Color(0xFF1E7B3C);
  static const Color pass = Color(0xFFD32F2F);
  static const Color superLike = Color(0xFFD9A21B);
}
