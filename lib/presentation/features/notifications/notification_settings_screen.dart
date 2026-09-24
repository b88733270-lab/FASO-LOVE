import 'package:faso_love/core/network/api_client.dart';
import 'package:flutter/material.dart';

/// Phase 8 — préférences de notification (cloche in-app + push).
///
/// Le push est téléscopiquement remplacé par des appels `GET/PUT /notifications/prefs`.
class NotificationSettingsScreen extends StatefulWidget {
  const NotificationSettingsScreen({super.key});

  @override
  State<NotificationSettingsScreen> createState() =>
      _NotificationSettingsScreenState();
}

class _NotificationSettingsScreenState
    extends State<NotificationSettingsScreen> {
  final ApiClient _api = ApiClient.instance;

  bool _matchs = true;
  bool _messages = true;
  bool _chargement = true;
  String? _erreur;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    try {
      final data = await _api.getJson('/notifications/prefs');
      if (!mounted) return;
      setState(() {
        _matchs = data['matches'] == true;
        _messages = data['messages'] == true;
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

  Future<void> _regler({bool? matchs, bool? messages}) async {
    final precedent = {'matches': _matchs, 'messages': _messages};
    setState(() {
      if (matchs != null) _matchs = matchs;
      if (messages != null) _messages = messages;
    });
    try {
      await _api.putJson('/notifications/prefs', {
        'matches': _matchs,
        'messages': _messages,
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _matchs = precedent['matches']!;
        _messages = precedent['messages']!;
      });
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Préférences de notification')),
      body: _chargement
          ? const Center(child: CircularProgressIndicator())
          : _erreur != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(_erreur!, textAlign: TextAlign.center),
                      const SizedBox(height: 12),
                      FilledButton(
                          onPressed: _charger,
                          child: const Text('Réessayer')),
                    ],
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.all(20),
                  children: [
                    const Text(
                      'Choisissez ce qui vous avertit — par cloche ou par '
                      'notification push. Vous pouvez tout couper, votre profil '
                      'reste visible normalement.',
                      style: TextStyle(color: Colors.black54),
                    ),
                    const SizedBox(height: 16),
                    SwitchListTile(
                      title: const Text('Nouveaux matchs 🎉'),
                      subtitle:
                          const Text('Quand une personne que vous avez likée '
                              'vous aime en retour'),
                      value: _matchs,
                      onChanged: (v) => _regler(matchs: v),
                    ),
                    SwitchListTile(
                      title: const Text('Nouveaux messages 💬'),
                      subtitle: const Text('Quand un match vous écrit'),
                      value: _messages,
                      onChanged: (v) => _regler(messages: v),
                    ),
                    const Divider(height: 32),
                    Text(
                      'Sandbox : les notifications push sont journalisées côté '
                      'serveur. En production, elles arrivent sur votre écran '
                      'verrouillé (Firebase Cloud Messaging).',
                      style: TextStyle(fontSize: 11, color: Colors.grey[500]),
                    ),
                  ],
                ),
    );
  }
}
