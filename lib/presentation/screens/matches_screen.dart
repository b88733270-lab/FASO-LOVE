import 'package:faso_love/core/network/api_client.dart';
import 'package:faso_love/core/utils/helpers/profile_image.dart';
import 'package:faso_love/data/models/chat/chat_models.dart';
import 'package:faso_love/presentation/screens/message_screen.dart';
import 'package:flutter/material.dart';

/// Onglet « Matchs » : conversations de matchs réciproques — donnée réelle
/// (`GET /matches`), rafraîchissement par glisser-relâcher.
class MatchesScreen extends StatefulWidget {
  const MatchesScreen({super.key});

  @override
  State<MatchesScreen> createState() => _MatchesScreenState();
}

class _MatchesScreenState extends State<MatchesScreen> {
  final ApiClient _api = ApiClient.instance;
  List<MatchSummary> _matchs = [];
  bool _chargement = true;
  String? _erreur;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    try {
      final liste = await _api.getList('/matches');
      if (!mounted) return;
      setState(() {
        _matchs = liste
            .map((m) => MatchSummary.fromJson(m as Map<String, dynamic>))
            .toList();
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

  Future<void> _ouvrir(MatchSummary match) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => MessageScreen(match: match),
      ),
    );
    _charger(); // rafraîchit badge non-lus / dernier message au retour
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Matchs'),
        automaticallyImplyLeading: false,
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
            const SizedBox(height: 8),
            TextButton(onPressed: _charger, child: const Text('Réessayer')),
          ],
        ),
      );
    }
    if (_matchs.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.favorite_border, size: 60, color: Colors.grey[300]),
            const SizedBox(height: 16),
            Text(
              'Aucun match pour le moment',
              style: TextStyle(fontSize: 20, color: Colors.grey[600]),
            ),
            const SizedBox(height: 8),
            Text(
              'Continuez à découvrir des profils !',
              style: TextStyle(color: Colors.grey[500]),
            ),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _charger,
      child: ListView.separated(
        padding: const EdgeInsets.all(8),
        itemCount: _matchs.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (context, index) {
          final m = _matchs[index];
          return ListTile(
            onTap: () => _ouvrir(m),
            leading: CircleAvatar(
              radius: 26,
              backgroundImage: m.peerAvatarUrl == null
                  ? null
                  : profileImageProvider(m.peerAvatarUrl!),
              child: m.peerAvatarUrl == null
                  ? const Icon(Icons.person, size: 28)
                  : null,
            ),
            title: Text(
              '${m.peerName}, ${m.peerAge}',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            subtitle: Text(
              m.lastMessage ?? 'À vous de jouer : brisez la glace 👋',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontStyle: m.lastMessage == null ? FontStyle.italic : null,
                color: m.unreadCount > 0 ? Colors.black87 : Colors.grey[600],
                fontWeight: m.unreadCount > 0 ? FontWeight.w600 : null,
              ),
            ),
            trailing: m.unreadCount > 0
                ? CircleAvatar(
                    radius: 12,
                    backgroundColor: Theme.of(context).colorScheme.primary,
                    child: Text(
                      '${m.unreadCount}',
                      style: const TextStyle(color: Colors.white, fontSize: 12),
                    ),
                  )
                : null,
          );
        },
      ),
    );
  }
}
