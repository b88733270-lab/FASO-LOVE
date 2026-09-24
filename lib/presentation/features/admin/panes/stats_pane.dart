import 'package:faso_love/core/constants/app_colors.dart';
import 'package:faso_love/core/network/api_client.dart';
import 'package:faso_love/data/models/admin/admin_models.dart';
import 'package:flutter/material.dart';

/// Panneau « Vue d'ensemble » : KPIs temps réel (GET /admin/stats).
class StatsPane extends StatefulWidget {
  const StatsPane({super.key});

  @override
  State<StatsPane> createState() => _StatsPaneState();
}

class _StatsPaneState extends State<StatsPane> {
  final ApiClient _api = ApiClient.instance;
  AdminStats? _stats;
  bool _chargement = true;
  String? _erreur;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    setState(() => _chargement = true);
    try {
      final data = await _api.getJson('/admin/stats');
      if (!mounted) return;
      setState(() {
        _stats = AdminStats.fromJson(data);
        _chargement = false;
        _erreur = null;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _chargement = false;
        _erreur = e.message;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _titre('Vue d\'ensemble', 'Activité de la plateforme en temps réel'),
          const SizedBox(height: 24),
          Expanded(child: _corps()),
        ],
      ),
    );
  }

  Widget _corps() {
    if (_chargement) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_erreur != null) {
      return AdminErreur(message: _erreur!, auReessai: _charger);
    }
    final s = _stats!;
    return RefreshIndicator(
      onRefresh: _charger,
      child: GridView.count(
        crossAxisCount: MediaQuery.of(context).size.width > 1300 ? 4 : 2,
        crossAxisSpacing: 20,
        mainAxisSpacing: 20,
        childAspectRatio: 1.9,
        children: [
          _carte('Utilisateurs', s.usersTotal, Icons.people, Colors.blue),
          _carte('Vérifiés (OTP)', s.usersVerified, Icons.verified_user,
              AppColors.primary),
          _carte('Actifs (24 h)', s.usersActiveToday, Icons.bolt,
              Colors.orange),
          _carte('Avec photo', s.profilesWithPhoto, Icons.photo_camera,
              Colors.teal),
          _carte('Matchs totaux', s.matchesTotal, Icons.favorite, Colors.pink),
          _carte('Messages', s.messagesTotal, Icons.chat_bubble_outline,
              Colors.indigo),
          _carte('Signalements en attente', s.reportsPending, Icons.flag,
              s.reportsPending > 0 ? Colors.red : Colors.green),
          _carte('Photos à modérer', s.photosPending, Icons.photo_library,
              s.photosPending > 0 ? Colors.deepOrange : Colors.green),
          // — Monétisation (Phase 7) —
          _carte('Abonnés Premium', s.subscriptionsActive, Icons.star,
              Colors.amber.shade700),
          _carte('Paiements confirmés', s.paymentsSucceeded, Icons.payments,
              Colors.green.shade700),
          _carte('Revenus (FCFA)', s.revenueFcfa, Icons.savings,
              Colors.purple),
        ],
      ),
    );
  }

  Widget _carte(String libelle, int valeur, IconData icone, Color couleur) {
    // Montants FCFA potentiellement à 6+ chiffres → taille adaptative.
    final longueur = '$valeur'.length;
    final taille = longueur > 6 ? 21.0 : (longueur > 4 ? 26.0 : 30.0);
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            CircleAvatar(
              radius: 26,
              backgroundColor: couleur.withOpacity(0.12),
              child: Icon(icone, color: couleur, size: 26),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    '$valeur',
                    style: TextStyle(
                      fontSize: taille,
                      fontWeight: FontWeight.bold,
                      color: couleur,
                    ),
                  ),
                  Text(libelle,
                      style: const TextStyle(color: Colors.black54),
                      maxLines: 2),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Titre d'un panneau admin (partagé).
Widget _titre(String titre, String sousTitre) {
  return Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(titre,
          style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
      const SizedBox(height: 4),
      Text(sousTitre, style: const TextStyle(color: Colors.black54)),
    ],
  );
}

/// Bloc titre partagé par les panneaux.
// ignore: non_constant_identifier_names
Widget AdminTitre({required String titre, required String sousTitre}) =>
    _titre(titre, sousTitre);

/// État d'erreur partagé par les panneaux (bouton « Réessayer »).
class AdminErreur extends StatelessWidget {
  final String message;
  final Future<void> Function() auReessai;

  const AdminErreur({super.key, required this.message, required this.auReessai});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(message, textAlign: TextAlign.center),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: auReessai,
            icon: const Icon(Icons.refresh),
            label: const Text('Réessayer'),
          ),
        ],
      ),
    );
  }
}
