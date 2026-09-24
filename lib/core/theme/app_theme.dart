import 'package:faso_love/core/constants/app_colors.dart';
import 'package:flutter/material.dart';

/// Thème Material de FASO LOVE (identité propre — palette AppColors).
final ThemeData appTheme = ThemeData(
  useMaterial3: true,
  colorScheme: ColorScheme.fromSeed(
    seedColor: AppColors.primary,
    primary: AppColors.primary,
    secondary: AppColors.secondary,
    error: AppColors.error,
  ),
  scaffoldBackgroundColor: Colors.white,
  appBarTheme: const AppBarTheme(
    elevation: 0,
    backgroundColor: Colors.white,
    foregroundColor: AppColors.textPrimary,
    iconTheme: IconThemeData(color: Colors.black54),
    titleTextStyle: TextStyle(
      fontSize: 24,
      fontWeight: FontWeight.bold,
      color: AppColors.primary,
    ),
  ),
  bottomNavigationBarTheme: const BottomNavigationBarThemeData(
    selectedItemColor: AppColors.primary,
    unselectedItemColor: Colors.grey,
    showSelectedLabels: true,
    showUnselectedLabels: true,
    type: BottomNavigationBarType.fixed,
  ),
);
