import 'package:faso_love/core/constants/app_colors.dart';
import 'package:faso_love/core/network/api_client.dart';
import 'package:faso_love/presentation/features/notifications/notification_settings_screen.dart';
import 'package:flutter/material.dart';

/// Phase 8 — centre de notifications (cloche in-app).
///
/// Liste les notifications récentes (match 🎉, message 💬) servies par
/// `GET /notifications`, affiche le badge, permet de marquer lu un élément
/// (tap) ou l'ensemble (« tout marquer lu »), et d'ouvrir les préférences.
class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  final ApiClient _api = ApiClient.instance;

  List<Map<String, dynamic>> _items = [];
  int _nonLues = 0;
  bool _chargement = true;
  String? _erreur;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    try {
      final data = await _api.getJson('/notifications');
      if (!mounted) return;
      setState(() {
        _items = (data['items'] as List).cast<Map<String, dynamic>>();
        _nonLues = (data['unread_count'] as num).toInt();
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

  Future<void> _marquerLu(Map<String, dynamic> notif) async {
    if (notif['read'] == true) return;
    // Optimiste : mise à jour visuelle immédiate.
    setState(() {
      notif['read'] = true;
      _nonLues = _nonLues > 0 ? _nonLues - 1 : 0;
    });
    try {
      await _api.postJson('/notifications/${notif['id']}/read', {});
    } catch (_) {/* la prochaine synchro corrigera */}
  }

  Future<void> _toutMarquerLu() async {
    try {
      await _api.postJson('/notifications/read-all', {});
      if (!mounted) return;
      setState(() {
        for (final n in _items) {
          n['read'] = true;
        }
        _nonLues = 0;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  String _date(String? iso) {
    final d = DateTime.tryParse(iso ?? '')?.toLocal();
    if (d == null) return '';
    final j = d.day.toString().padLeft(2, '0');
    final m = d.month.toString().padLeft(2, '0');
    final h = d.hour.toString().padLeft(2, '0');
    final mi = d.minute.toString().padLeft(2, '0');
    return '$j/$m à $h:$mi';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const Text('Notifications'),
            if (_nonLues > 0) ...[
              const SizedBox(width: 8),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '$_nonLues',
                  style: const TextStyle(color: Colors.white, fontSize: 12),
                ),
              ),
            ],
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            tooltip: 'Préférences',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(
                  builder: (_) => const NotificationSettingsScreen()),
            ),
          ),
          if (_nonLues > 0)
            TextButton(
              onPressed: _toutMarquerLu,
              child: const Text(
                'Tout marquer lu',
                style: TextStyle(color: Colors.white, fontSize: 12),
              ),
            ),
        ],
      ),
      body: _corps(),
    );
  }

  Widget _corps() {
    if (_chargement) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_erreur != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(_erreur!, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton(onPressed: _charger, child: const Text('Réessayer')),
          ],
        ),
      );
    }
    if (_items.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.notifications_none, size: 64, color: Colors.grey),
              SizedBox(height: 12),
              Text(
                'Aucune notification pour le moment.\n'
                'Un match ou un message viendra remplir cette cloche !',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey),
              ),
            ],
          ),
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _charger,
      child: ListView.separated(
        itemCount: _items.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (context, i) => _ligne(_items[i]),
      ),
    );
  }

  Widget _ligne(Map<String, dynamic> n) {
    final lue = n['read'] == true;
    final kind = n['kind'];
    final iconData = kind == 'match'
        ? Icons.favorite
        : kind == 'message'
            ? Icons.chat_bubble_outline
            : Icons.notifications_outlined;
    final couleur = kind == 'match' ? Colors.pink : Colors.indigo;
    return ListTile(
      onTap: () => _marquerLu(n),
      tileColor: lue ? null : const Color(0xFFFFF6E8),
      leading: CircleAvatar(
        backgroundColor: couleur.withOpacity(0.12),
        child: Icon(iconData, color: couleur),
      ),
      title: Text(
        '${n['title']}',
        style: TextStyle(fontWeight: lue ? FontWeight.normal : FontWeight.bold),
      ),
      subtitle: Text(
        '${n['body']}\n${_date(n['created_at']?.toString())}',
        maxLines: 3,
      ),
      isThreeLine: true,
      trailing: lue
          ? null
          : const Icon(Icons.fiber_manual_record, size: 12,
              color: AppColors.primary),
    );
  }
}
