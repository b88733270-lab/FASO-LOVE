import 'package:faso_love/core/theme/app_theme.dart';
import 'package:faso_love/data/providers/auth_session.dart';
import 'package:faso_love/presentation/features/auth/login_screen.dart';
import 'package:faso_love/presentation/screens/home_screen.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

void main() {
  runApp(
    ChangeNotifierProvider(
      create: (_) => AuthSession(),
      child: const FasoLoveApp(),
    ),
  );
}

/// FASO LOVE — application de rencontre (18+) pour le Burkina Faso.
///
/// Ce produit intègre du code du projet open-source « SparkMatch »
/// (licence MIT, © 2025 Harendra Prajapati) — voir LICENSE et NOTICE.md.
///
/// TODO(phase-6) : routage nommé avec garde d'authentification, l10n
/// (fr/mooré/dioula) et reporting d'erreurs (Sentry).
class FasoLoveApp extends StatelessWidget {
  const FasoLoveApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FASO LOVE',
      debugShowCheckedModeBanner: false,
      theme: appTheme,
      home: Consumer<AuthSession>(
        builder: (context, session, _) {
          // Garde d'authentification : rien d'autre n'est accessible
          // sans session OTP validée (règle 18+ appliquée côté serveur).
          if (session.estConnecte) {
            return const HomeScreen();
          }
          return const LoginScreen();
        },
      ),
    );
  }
}
