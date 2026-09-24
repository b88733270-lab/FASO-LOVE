import 'package:faso_love/core/config/api_config.dart';

/// KPIs du tableau de bord (`GET /admin/stats` → AdminStatsOut).
class AdminStats {
  final int usersTotal;
  final int usersVerified;
  final int usersActiveToday;
  final int profilesWithPhoto;
  final int matchesTotal;
  final int messagesTotal;
  final int reportsPending;
  final int photosPending;
  final int subscriptionsActive;
  final int paymentsSucceeded;
  final int revenueFcfa;

  const AdminStats({
    required this.usersTotal,
    required this.usersVerified,
    required this.usersActiveToday,
    required this.profilesWithPhoto,
    required this.matchesTotal,
    required this.messagesTotal,
    required this.reportsPending,
    required this.photosPending,
    this.subscriptionsActive = 0,
    this.paymentsSucceeded = 0,
    this.revenueFcfa = 0,
  });

  factory AdminStats.fromJson(Map<String, dynamic> json) => AdminStats(
        usersTotal: (json['users_total'] as num?)?.toInt() ?? 0,
        usersVerified: (json['users_verified'] as num?)?.toInt() ?? 0,
        usersActiveToday: (json['users_active_today'] as num?)?.toInt() ?? 0,
        profilesWithPhoto: (json['profiles_with_photo'] as num?)?.toInt() ?? 0,
        matchesTotal: (json['matches_total'] as num?)?.toInt() ?? 0,
        messagesTotal: (json['messages_total'] as num?)?.toInt() ?? 0,
        reportsPending: (json['reports_pending'] as num?)?.toInt() ?? 0,
        photosPending: (json['photos_pending'] as num?)?.toInt() ?? 0,
        subscriptionsActive:
            (json['subscriptions_active'] as num?)?.toInt() ?? 0,
        paymentsSucceeded:
            (json['payments_succeeded'] as num?)?.toInt() ?? 0,
        revenueFcfa: (json['revenue_fcfa_total'] as num?)?.toInt() ?? 0,
      );
}

/// Élément de la file de signalements (`GET /admin/reports` → AdminReportItem).
class AdminReport {
  final String id;
  final String reporterId;
  final String reportedId;
  final String reportedName;
  final String reason;
  final String details;
  final String status;
  final DateTime? createdAt;

  AdminReport({
    required this.id,
    required this.reporterId,
    required this.reportedId,
    required this.reportedName,
    required this.reason,
    required this.details,
    required this.status,
    this.createdAt,
  });

  factory AdminReport.fromJson(Map<String, dynamic> json) => AdminReport(
        id: json['id'] as String,
        reporterId: json['reporter_id'] as String? ?? '',
        reportedId: json['reported_id'] as String? ?? '',
        reportedName: (json['reported_name'] as String?) ?? 'Profil inconnu',
        reason: json['reason'] as String? ?? 'other',
        details: (json['details'] as String?) ?? '',
        status: json['status'] as String? ?? 'pending',
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
      );

  static const Map<String, String> motifs = {
    'harassment': 'Harcèlement',
    'spam': 'Spam / publicité',
    'fake': 'Faux profil',
    'scam': '⚠️ Arnaque / demande d\'argent',
    'inappropriate': 'Contenu inapproprié',
    'underage': '🚨 Mineur présumé',
    'other': 'Autre',
  };

  String get motifLibelle => motifs[reason] ?? reason;

  /// Les signalements d'arnaque et de mineur sont traités en priorité.
  bool get estPrioritaire => reason == 'scam' || reason == 'underage';
}

/// Ligne utilisateur du back-office (`GET /admin/users` → AdminUserItem).
class AdminUser {
  final String id;
  final String phone;
  final int? age;
  final String role;
  final bool isActive;
  final bool isVerified;
  final String displayName;
  final String city;
  final DateTime? createdAt;

  AdminUser({
    required this.id,
    required this.phone,
    required this.role,
    required this.isActive,
    required this.isVerified,
    required this.displayName,
    required this.city,
    this.age,
    this.createdAt,
  });

  factory AdminUser.fromJson(Map<String, dynamic> json) => AdminUser(
        id: json['id'] as String,
        phone: json['phone_e164'] as String? ?? '',
        age: (json['age'] as num?)?.toInt(),
        role: json['role'] as String? ?? 'user',
        isActive: json['is_active'] as bool? ?? true,
        isVerified: json['is_verified'] as bool? ?? false,
        displayName: (json['display_name'] as String?) ?? '—',
        city: (json['city'] as String?) ?? '',
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
      );
}

/// Photo en attente de validation (`GET /admin/photos` → AdminPhotoItem).
class AdminPhoto {
  final String id;
  final String userId;
  final String url;
  final String status;
  final DateTime? createdAt;

  AdminPhoto({
    required this.id,
    required this.userId,
    required this.url,
    required this.status,
    this.createdAt,
  });

  /// URL relative /media/… → absolue (chargée par Image.network).
  String get urlAbsolue => ApiConfig.absolute(url);

  factory AdminPhoto.fromJson(Map<String, dynamic> json) => AdminPhoto(
        id: json['id'] as String,
        userId: json['user_id'] as String? ?? '',
        url: json['url'] as String? ?? '',
        status: json['status'] as String? ?? 'pending',
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
      );
}
