import 'package:flutter/material.dart';

const _darkBackground = Color(0xFF1A1A2E);
const _tealAccent = Color(0xFF00B4D8);

final mobiusTheme = ThemeData(
  useMaterial3: true,
  brightness: Brightness.dark,
  scaffoldBackgroundColor: _darkBackground,
  colorScheme: ColorScheme.dark(
    background: _darkBackground,
    primary: _tealAccent,
    secondary: _tealAccent,
    surface: const Color(0xFF16213E),
  ),
  appBarTheme: const AppBarTheme(
    backgroundColor: _darkBackground,
    foregroundColor: Colors.white,
    elevation: 0,
  ),
  inputDecorationTheme: InputDecorationTheme(
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: _tealAccent),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: _tealAccent, width: 2),
    ),
  ),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      backgroundColor: _tealAccent,
      foregroundColor: Colors.black,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 24),
    ),
  ),
);
