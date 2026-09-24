import 'package:faso_love/core/constants/app_colors.dart';
import 'package:faso_love/data/push_service.dart';
import 'package:faso_love/presentation/screens/discover_screen.dart';
import 'package:faso_love/presentation/screens/explore_screen.dart';
import 'package:faso_love/presentation/screens/matches_screen.dart';
import 'package:faso_love/presentation/screens/profile_screen.dart';
import 'package:flutter/material.dart';

/// Écran d'accueil FASO LOVE : navigation à 4 onglets.
///
/// TODO(phase-1) : remplacer par un routage nommé avec garde d'auth
/// (redirection vers l'onboarding si l'utilisateur n'est pas connecté).
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  @override
  void initState() {
    super.initState();
    // Phase 8 — l'utilisateur connecté qui ouvre l'app enregistre son
    // appareil pour la cloche/push (sandbox FCM, idempotent, silencieux).
    WidgetsBinding.instance.addPostFrameCallback((_) {
      PushService.instance.enregistrer();
    });
  }

  final List<Widget> _screens = [
    const DiscoverScreen(),
    const MatchesScreen(),
    const ExploreScreen(),
    const ProfileScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        type: BottomNavigationBarType.fixed,
        selectedItemColor: AppColors.primary,
        unselectedItemColor: Colors.grey,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.home_filled),
            label: 'Découvrir',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.favorite_border),
            label: 'Matchs',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.explore_outlined),
            label: 'Explorer',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.person_outline),
            label: 'Profil',
          ),
        ],
      ),
    );
  }
}
