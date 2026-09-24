import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:faso_love/core/config/api_config.dart';
import 'package:faso_love/core/constants/app_colors.dart';
import 'package:faso_love/core/network/api_client.dart';
import 'package:faso_love/core/utils/helpers/profile_image.dart';
import 'package:faso_love/data/models/chat/chat_models.dart';
import 'package:faso_love/data/providers/auth_session.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

/// Conversation 1-à-1 temps réel : historique REST + WebSocket
/// (`/ws/chat/{match_id}`) avec repli REST quand le socket est coupé
/// (bas débit). Réservée aux utilisateurs matchés.
class MessageScreen extends StatefulWidget {
  final MatchSummary match;

  const MessageScreen({super.key, required this.match});

  @override
  State<MessageScreen> createState() => _MessageScreenState();
}

class _MessageScreenState extends State<MessageScreen> {
  final ApiClient _api = ApiClient.instance;
  final TextEditingController _saisie = TextEditingController();
  final List<ChatMessage> _messages = []; // ordre chronologique inverse
  final ScrollController _scroll = ScrollController();

  WebSocket? _socket;
  StreamSubscription<dynamic>? _abonnement;
  Timer? _hebdo;
  Timer? _finTyping;

  String? _erreur;
  bool _chargement = true;
  bool _typingPair = false;
  String get _monId =>
      context.read<AuthSession>().myUserId ?? '_inconnu_';

  @override
  void initState() {
    super.initState();
    _chargerHistorique().then((_) => _connecterSocket());
  }

  @override
  void dispose() {
    _abonnement?.cancel();
    _socket?.close();
    _hebdo?.cancel();
    _finTyping?.cancel();
    _saisie.dispose();
    _scroll.dispose();
    super.dispose();
  }

  // ------------------------------------------------------------- historique

  Future<void> _chargerHistorique() async {
    try {
      final liste = await _api
          .getList('/matches/${widget.match.matchId}/messages?limit=50');
      if (!mounted) return;
      setState(() {
        _messages
          ..clear()
          ..addAll(liste.map((m) => ChatMessage.fromJson(
                m as Map<String, dynamic>,
                myUserId: _monId,
              )));
        _chargement = false;
      });
      _marquerVus();
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _chargement = false;
        _erreur = e.message;
      });
    }
  }

  Future<void> _marquerVus() async {
    try {
      await _api.postJson('/matches/${widget.match.matchId}/read', {});
    } catch (_) {/* non bloquant */}
  }

  // ---------------------------------------------------------------- socket

  Future<void> _connecterSocket() async {
    final token = _api.accessToken;
    if (token == null) return;
    try {
      final socket = await WebSocket.connect(
        ApiConfig.chatSocketUrl(widget.match.matchId, token),
      );
      if (!mounted) {
        await socket.close();
        return;
      }
      _socket = socket;
      _abonnement = socket.listen(_surEvenement, onDone: _surCoupure,
          onError: (_) => _surCoupure());
      setState(() => _erreur = null);
    } catch (_) {
      // Mode repli REST : on reste fonctionnel (rafraîchissement périodique).
      _hebdo ??= Timer.periodic(const Duration(seconds: 12), (_) {
        _chargerHistorique();
      });
    }
  }

  void _surCoupure() {
    _socket = null;
    _hebdo ??= Timer.periodic(const Duration(seconds: 12), (_) {
      _chargerHistorique();
    });
    if (mounted) setState(() {});
  }

  void _surEvenement(dynamic brut) {
    Map<String, dynamic> data;
    try {
      data = json.decode(brut as String) as Map<String, dynamic>;
    } catch (_) {
      return;
    }
    switch (data['type']) {
      case 'message':
        final message = ChatMessage.fromJson(
          data['message'] as Map<String, dynamic>,
          myUserId: _monId,
        );
        if (!_messages.any((m) => m.id == message.id)) {
          setState(() => _messages.insert(0, message));
        }
        if (!message.isMine) {
          _typingPair = false;
          _marquerVus();
        }
        break;
      case 'typing':
        // Frame backend : {"type":"typing","user_id":…} (sans durée) →
        // on affiche l'indicateur 4 s, extinction automatique.
        if (!mounted) return;
        _finTyping?.cancel();
        _finTyping = Timer(const Duration(seconds: 4), () {
          if (mounted) setState(() => _typingPair = false);
        });
        setState(() => _typingPair = true);
        break;
      case 'read':
        // Frame backend : {"type":"read","by":id} → mes messages lus.
        if (mounted) {
          final readAt = DateTime.now().toIso8601String();
          setState(() {
            for (var i = 0; i < _messages.length; i++) {
              final m = _messages[i];
              if (m.isMine && m.readAt == null) {
                _messages[i] = ChatMessage(
                  id: m.id,
                  senderId: m.senderId,
                  content: m.content,
                  createdAt: m.createdAt,
                  readAt: readAt,
                  isMine: true,
                );
              }
            }
          });
        }
        break;
    }
  }

  // ------------------------------------------------------------------ envoi

  Future<void> _envoyer() async {
    final texte = _saisie.text.trim();
    if (texte.isEmpty) return;
    _saisie.clear();
    final socket = _socket;
    if (socket != null && socket.readyState == WebSocket.open) {
      socket.add(json.encode({'type': 'message', 'content': texte}));
      return;
    }
    // Repli REST (bas débit) puis insertion locale.
    try {
      final envoye = await _api.postJson(
        '/matches/${widget.match.matchId}/messages',
        {'content': texte},
      );
      if (!mounted) return;
      setState(() {
        _messages.insert(
          0,
          ChatMessage.fromJson(envoye, myUserId: _monId),
        );
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _erreur = e.message);
    }
  }

  void _signalerTyping() {
    final socket = _socket;
    if (socket != null && socket.readyState == WebSocket.open) {
      socket.add(json.encode({'type': 'typing'}));
    }
  }

  // ------------------------------------------------------------------- vue

  static const List<Map<String, String>> _motifsSignalement = [
    {'code': 'harassment', 'libelle': 'Harcèlement'},
    {'code': 'spam', 'libelle': 'Spam / publicité'},
    {'code': 'fake', 'libelle': 'Faux profil'},
    {'code': 'scam', 'libelle': 'Arnaque / demande d\'argent'},
    {'code': 'inappropriate', 'libelle': 'Contenu inapproprié'},
    {'code': 'underage', 'libelle': 'Utilisateur mineur présumé'},
    {'code': 'other', 'libelle': 'Autre'},
  ];

  Future<void> _signaler() async {
    final motif = await showModalBottomSheet<String>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text(
                'Pourquoi signalez-vous ce profil ?',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
            ),
            for (final m in _motifsSignalement)
              ListTile(
                title: Text(m['libelle']!),
                onTap: () => Navigator.of(context).pop(m['code']),
              ),
          ],
        ),
      ),
    );
    if (motif == null || !mounted) return;
    try {
      await _api.postJson('/reports', {
        'reported_user_id': widget.match.peerUserId,
        'reason': motif,
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Merci. Notre équipe va vérifier.')),
      );
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  String _heure(String iso) {
    final date = DateTime.tryParse(iso)?.toLocal();
    if (date == null) return '';
    return '${date.hour} h ${date.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final match = widget.match;
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            CircleAvatar(
              backgroundImage: match.peerAvatarUrl == null
                  ? null
                  : profileImageProvider(match.peerAvatarUrl!),
              radius: 16,
              child: match.peerAvatarUrl == null
                  ? const Icon(Icons.person, size: 18)
                  : null,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(match.peerName),
                  if (_typingPair)
                    const Text(
                      'en train d\'écrire…',
                      style: TextStyle(fontSize: 12, color: Colors.white70),
                    ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.more_vert),
            tooltip: 'Signaler',
            onPressed: _signaler,
          ),
        ],
      ),
      body: Column(
        children: [
          // Bandeau de prévention anti-arnaque (sécurité des utilisateurs).
          Container(
            width: double.infinity,
            color: AppColors.secondaryLight.withOpacity(0.35),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: const Text(
              'Conseil : ne partagez jamais d’argent ni vos informations personnelles avec un inconnu.',
              style: TextStyle(fontSize: 12),
              textAlign: TextAlign.center,
            ),
          ),
          if (_erreur != null)
            Container(
              width: double.infinity,
              color: Colors.red.shade50,
              padding: const EdgeInsets.all(6),
              child: Text(
                _erreur!,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 12, color: Colors.red),
              ),
            ),
          Expanded(
            child: _chargement
                ? const Center(child: CircularProgressIndicator())
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    reverse: true,
                    controller: _scroll,
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      final message = _messages[index];
                      return _buildMessageBubble(message);
                    },
                  ),
          ),
          _buildMessageInput(),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(ChatMessage message) {
    final isMe = message.isMine;
    return Align(
      alignment: isMe ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        decoration: BoxDecoration(
          color: isMe
              ? AppColors.primaryLight.withOpacity(0.35)
              : Colors.grey[200],
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(message.content, style: const TextStyle(fontSize: 16)),
            const SizedBox(height: 4),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _heure(message.createdAt),
                  style: TextStyle(fontSize: 10, color: Colors.grey[600]),
                ),
                if (isMe) ...[
                  const SizedBox(width: 4),
                  Icon(
                    message.readAt != null ? Icons.done_all : Icons.check,
                    size: 12,
                    color: message.readAt != null
                        ? AppColors.primary
                        : Colors.grey[600],
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMessageInput() {
    return SafeArea(
      child: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Colors.white,
          boxShadow: [
            BoxShadow(
              color: Colors.grey.withOpacity(0.2),
              blurRadius: 8,
              spreadRadius: 2,
            ),
          ],
        ),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: _saisie,
                textCapitalization: TextCapitalization.sentences,
                onChanged: (_) => _signalerTyping(),
                onSubmitted: (_) => _envoyer(),
                decoration: InputDecoration(
                  hintText: 'Écrire un message…',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(24),
                    borderSide: BorderSide.none,
                  ),
                  filled: true,
                  fillColor: Colors.grey[100],
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 16),
                ),
              ),
            ),
            IconButton(
              icon: const Icon(Icons.send),
              tooltip: 'Envoyer',
              color: AppColors.primary,
              onPressed: _envoyer,
            ),
          ],
        ),
      ),
    );
  }
}
