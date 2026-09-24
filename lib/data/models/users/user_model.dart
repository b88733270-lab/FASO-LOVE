import 'package:faso_love/core/config/api_config.dart';

class User {
  final String id;
  final String name;
  final int age;
  final String photoUrl;
  final String bio;
  final double distance;
  final List<String> interests;
  final String city;

  User({
    required this.id,
    required this.name,
    required this.age,
    required this.photoUrl,
    required this.bio,
    required this.distance,
    required this.interests,
    this.city = '',
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      name: json['name'],
      age: json['age'],
      photoUrl: json['photoUrl'],
      bio: json['bio'],
      distance: json['distance'].toDouble(),
      interests: List<String>.from(json['interests']),
    );
  }

  /// Carte de découverte renvoyée par `GET /discover` (schéma ProfilePublic :
  /// `photos` = liste d'objets {id, url, status}, URL relatives /media/…).
  factory User.fromDiscoverJson(Map<String, dynamic> json) {
    final photos = (json['photos'] as List?) ?? const [];
    String first = '';
    if (photos.isNotEmpty) {
      final p = photos.first;
      first = p is Map ? (p['url'] as String? ?? '') : p as String;
    }
    return User(
      id: json['user_id'] as String,
      name: json['display_name'] as String,
      age: (json['age'] as num).toInt(),
      photoUrl: first.isEmpty ? '' : ApiConfig.absolute(first),
      bio: (json['bio'] as String?) ?? '',
      distance: (json['distance_km'] as num?)?.toDouble() ?? 0,
      interests: List<String>.from((json['interests'] as List?) ?? const []),
      city: (json['city'] as String?) ?? '',
    );
  }
}
