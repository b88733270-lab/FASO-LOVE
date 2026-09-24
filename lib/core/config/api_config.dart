/// Configuration réseau FASO LOVE.
///
/// L'URL de l'API est injectée à la compilation :
///   flutter run --dart-define=API_URL=https://xxx-8000.e2b.app
///
/// Défauts développement :
/// - émulateur Android : http://10.0.2.2:8000 (hôte de la machine) ;
/// - iOS / web / desktop : http://localhost:8000.
library;

class ApiConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  static const String apiPrefix = '/api/v1';

  /// Base HTTP complète (ex. http://10.0.2.2:8000/api/v1).
  static String get apiBase => '$baseUrl$apiPrefix';

  /// URL WebSocket complète pour le chat d'un match.
  static String chatSocketUrl(String matchId, String token) {
    final ws = baseUrl.replaceFirst(RegExp(r'^http'), 'ws');
    return '$ws$apiPrefix/ws/chat/$matchId?token=$token';
  }

  /// Rend absolue une URL relative renvoyée par l'API (ex. /media/x.jpg).
  static String absolute(String path) {
    if (path.startsWith('http')) return path;
    return '$baseUrl$path';
  }
}
