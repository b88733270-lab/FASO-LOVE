import 'package:faso_love/core/config/api_config.dart';

/// Résumé d'un match tel que renvoyé par `GET /matches`
/// (schéma MatchOut : match_id, created_at, peer{…}, last_message, unread).
class MatchSummary {
  final String matchId;
  final String peerUserId;
  final String peerName;
  final int peerAge;
  final String? peerAvatarUrl;
  final String city;
  final List<String> peerInterests;
  final String? lastMessage;
  final String? lastMessageAt;
  final bool lastMessageIsMine;
  final int unreadCount;
  final String matchedAt;

  const MatchSummary({
    required this.matchId,
    required this.peerUserId,
    required this.peerName,
    required this.peerAge,
    required this.city,
    required this.matchedAt,
    required this.peerInterests,
    this.peerAvatarUrl,
    this.lastMessage,
    this.lastMessageAt,
    this.lastMessageIsMine = false,
    this.unreadCount = 0,
  });

  factory MatchSummary.fromJson(Map<String, dynamic> json) {
    final peer = json['peer'] as Map<String, dynamic>;
    final photo = peer['photo_url'] as String?;
    final last = json['last_message'] as Map<String, dynamic>?;
    return MatchSummary(
      matchId: json['match_id'] as String,
      peerUserId: peer['user_id'] as String,
      peerName: peer['display_name'] as String,
      peerAge: (peer['age'] as num).toInt(),
      peerAvatarUrl: photo == null ? null : ApiConfig.absolute(photo),
      city: (peer['city'] as String?) ?? '',
      peerInterests:
          List<String>.from((peer['interests'] as List?) ?? const []),
      lastMessage: last?['content'] as String?,
      lastMessageAt: last?['created_at'] as String?,
      lastMessageIsMine: (last?['is_mine'] as bool?) ?? false,
      unreadCount: (json['unread_count'] as num?)?.toInt() ?? 0,
      matchedAt: (json['created_at'] as String?) ?? '',
    );
  }
}

/// Message de conversation (REST historique ou payload WebSocket).
class ChatMessage {
  final String id;
  final String senderId;
  final String content;
  final String createdAt;
  final String? readAt;
  final bool isMine;

  const ChatMessage({
    required this.id,
    required this.senderId,
    required this.content,
    required this.createdAt,
    this.readAt,
    this.isMine = false,
  });

  /// `GET /matches/{id}/messages` renvoie `is_mine` calculé ; les événements
  /// WebSocket non — on le déduit alors de [myUserId].
  factory ChatMessage.fromJson(
    Map<String, dynamic> json, {
    required String myUserId,
  }) {
    final senderId = json['sender_id'] as String;
    final isMineFlag =
        (json['is_mine'] as bool?) == true || senderId == myUserId;
    return ChatMessage(
      id: json['id'] as String,
      senderId: senderId,
      content: json['content'] as String,
      createdAt: json['created_at'] as String? ?? '',
      readAt: json['read_at'] as String?,
      isMine: isMineFlag,
    );
  }
}
