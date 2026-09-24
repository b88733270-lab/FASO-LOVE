import 'package:faso_love/core/theme/app_theme.dart';
import 'package:faso_love/data/providers/auth_session.dart';
import 'package:faso_love/presentation/features/admin/admin_home_screen.dart';
import 'package:faso_love/presentation/features/auth/login_screen.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

void main() {
  runApp(
    ChangeNotifierProvider(
      create: (_) => AuthSession(),
      child: const FasoLoveAdminApp(),
    ),
  );
}

/// FASO LOVE — Console d'administration (Flutter Web).
///
/// Lancement : `flutter run -d chrome -t lib/main_admin.dart`
///             --dart-define=API_URL=https://VOTRE_API
///
/// Double garde de sécurité :
/// 1. authentification OTP obligatoire (même réseau de comptes) ;
/// 2. rôle « admin » attribué CÔTÉ SERVEUR uniquement — l'API répond 403
///    à tout non-admin même sans cette garde d'interface.
class FasoLoveAdminApp extends StatelessWidget {
  const FasoLoveAdminApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FASO LOVE — Console admin',
      debugShowCheckedModeBanner: false,
      theme: appTheme,
      home: Consumer<AuthSession>(
        builder: (context, session, _) {
          if (!session.estConnecte) {
            return const LoginScreen();
          }
          if (!session.estAdmin) {
            return _AccesRefuse(session: session);
          }
          return const AdminHomeScreen();
        },
      ),
    );
  }
}

/// Écran affiché à un compte connecté mais dépourvu du rôle admin.
class _AccesRefuse extends StatelessWidget {
  final AuthSession session;

  const _AccesRefuse({required this.session});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.lock_outline, size: 64, color: Colors.grey[400]),
              const SizedBox(height: 16),
              const Text(
                'Accès réservé à l\'équipe de modération',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                'Le compte ${session.myPhone ?? ''} n\'a pas les droits '
                'd\'administration. Contactez votre responsable si vous '
                'pensez qu\'il s\'agit d\'une erreur.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.black54),
              ),
              const SizedBox(height: 24),
              OutlinedButton.icon(
                onPressed: session.seDeconnecter,
                icon: const Icon(Icons.logout),
                label: const Text('Se déconnecter'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
