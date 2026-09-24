import 'package:faso_love/core/constants/app_colors.dart';
import 'package:faso_love/presentation/features/admin/panes/photos_pane.dart';
import 'package:faso_love/presentation/features/admin/panes/reports_pane.dart';
import 'package:faso_love/presentation/features/admin/panes/stats_pane.dart';
import 'package:faso_love/presentation/features/admin/panes/users_pane.dart';
import 'package:flutter/material.dart';

/// Coquille de la console d'administration (Flutter Web, écrans larges) :
/// rail de navigation à gauche + panneau de contenu à droite.
class AdminHomeScreen extends StatefulWidget {
  const AdminHomeScreen({super.key});

  @override
  State<AdminHomeScreen> createState() => _AdminHomeScreenState();
}

class _AdminHomeScreenState extends State<AdminHomeScreen> {
  int _index = 0;

  static const _panes = [
    StatsPane(),
    ReportsPane(),
    UsersPane(),
    PhotosPane(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          NavigationRail(
            extended: MediaQuery.of(context).size.width > 1100,
            selectedIndex: _index,
            onDestinationSelected: (i) => setState(() => _index = i),
            selectedIconTheme: const IconThemeData(color: AppColors.primary),
            selectedLabelTextStyle:
                const TextStyle(color: AppColors.primary, fontWeight: FontWeight.bold),
            labelType: MediaQuery.of(context).size.width > 1100
                ? NavigationRailLabelType.none
                : NavigationRailLabelType.all,
            leading: const Padding(
              padding: EdgeInsets.symmetric(vertical: 20),
              child: Icon(Icons.favorite, color: AppColors.primary, size: 32),
            ),
            destinations: const [
              NavigationRailDestination(
                icon: Icon(Icons.insights_outlined),
                selectedIcon: Icon(Icons.insights),
                label: Text('Vue d\'ensemble'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.flag_outlined),
                selectedIcon: Icon(Icons.flag),
                label: Text('Signalements'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.people_outline),
                selectedIcon: Icon(Icons.people),
                label: Text('Utilisateurs'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.photo_library_outlined),
                selectedIcon: Icon(Icons.photo_library),
                label: Text('Modération photos'),
              ),
            ],
          ),
          const VerticalDivider(width: 1),
          Expanded(
            child: Container(
              color: const Color(0xFFF6F7F9),
              child: IndexedStack(index: _index, children: _panes),
            ),
          ),
        ],
      ),
    );
  }
}
