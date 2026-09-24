import 'package:faso_love/core/constants/app_colors.dart';
import 'package:faso_love/core/network/api_client.dart';
import 'package:faso_love/presentation/features/notifications/notifications_screen.dart';
import 'package:flutter/material.dart';

/// Phase 8 — picto cloche avec badge (écran Découvrir).
///
/// Interroge le compteur léger `GET /notifications/count` au montage,
/// s'actualise à chaque retour depuis le centre de notifications, et le
/// re-tire périodiquement (toutes les 60 s tant que l'écran est visible)
/// pour suivre les événements reçus en arrière-plan.
class NotificationBell extends StatefulWidget {
  const NotificationBell({super.key});

  @override
  State<NotificationBell> createState() => _NotificationBellState();
}

class _NotificationBellState extends State<NotificationBell> {
  final ApiClient _api = ApiClient.instance;
  int _nonLues = 0;
  DateTime _dernierTir = DateTime.fromMillisecondsSinceEpoch(0);

  @override
  void initState() {
    super.initState();
    _rafraichir(force: true);
    // Auto-tir doux, tant que le widget vit (léger : 1 requête/min).
    Future.doWhile(() async {
      await Future.delayed(const Duration(seconds: 60));
      if (!mounted) return false;
      _rafraichir();
      return true;
    });
  }

  Future<void> _rafraichir({bool force = false}) async {
    if (!force && DateTime.now().difference(_dernierTir).inSeconds < 5) {
      return;
    }
    _dernierTir = DateTime.now();
    try {
      final data = await _api.getJson('/notifications/count');
      if (!mounted) return;
      setState(() => _nonLues = (data['unread_count'] as num).toInt());
    } catch (_) {/* badge muet plutôt qu'écran casse */}
  }

  Future<void> _ouvrir() async {
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const NotificationsScreen()),
    );
    _rafraichir(force: true);
  }

  @override
  Widget build(BuildContext context) {
    return IconButton(
      tooltip: 'Notifications',
      onPressed: _ouvrir,
      icon: Stack(
        clipBehavior: Clip.none,
        children: [
          const Icon(Icons.notifications_outlined),
          if (_nonLues > 0)
            Positioned(
              right: -4,
              top: -4,
              child: Container(
                padding: const EdgeInsets.all(4),
                constraints: const BoxConstraints(minWidth: 18, minHeight: 18),
                decoration: const BoxDecoration(
                  color: AppColors.primary,
                  shape: BoxShape.circle,
                ),
                child: Text(
                  _nonLues > 99 ? '99+' : '$_nonLues',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 10, color: Colors.white),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
