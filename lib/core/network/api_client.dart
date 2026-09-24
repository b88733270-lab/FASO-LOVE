import 'dart:async';
import 'dart:convert';
import 'dart:io';

import '../config/api_config.dart';

/// Erreur d'API : [message] est la formulation FRANÇAISE du serveur
/// (champ `detail`) lorsqu'elle existe, à afficher telle quelle.
class ApiException implements Exception {
  final int statusCode;
  final String message;

  ApiException(this.statusCode, this.message);

  bool get isUnauthorized => statusCode == 401;

  @override
  String toString() => message;
}

/// Client HTTP minimal FASO LOVE — **sans dépendance externe**
/// (`dart:io` natif, compatible bas débit : JSON compact, timeout court).
///
/// - Bearer token injecté automatiquement ;
/// - rafraîchissement automatique du jeton d'accès (1 seule reprise) ;
/// - upload multipart manuel pour les photos de profil ;
/// - WebSocket natif pour le chat temps réel.
class ApiClient {
  ApiClient._();

  static final ApiClient instance = ApiClient._();

  String? _accessToken;
  String? _refreshToken;

  static const Duration _timeout = Duration(seconds: 20);

  String? get accessToken => _accessToken;

  /// Enregistre les jetons après connexion/rafraîchissement.
  void setTokens({required String accessToken, required String refreshToken}) {
    _accessToken = accessToken;
    _refreshToken = refreshToken;
  }

  void clearTokens() {
    _accessToken = null;
    _refreshToken = null;
  }

  bool get hasSession => _accessToken != null;

  // ---------------------------------------------------------------- helpers

  Future<HttpClientRequest> _request(String method, String path) async {
    final client = HttpClient()..connectionTimeout = _timeout;
    final request = await client.openUrl(
      method,
      Uri.parse('${ApiConfig.apiBase}$path'),
    );
    if (_accessToken != null) {
      request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $_accessToken');
    }
    return request;
  }

  Future<Map<String, dynamic>> _send(
    HttpClientRequest request, {
    bool retried = false,
  }) async {
    final response = await request.close().timeout(_timeout);
    final body = await utf8.decoder.bind(response).join();
    if (response.statusCode == 401 && !retried && await tryRefresh()) {
      throw _RetryAfterRefresh();
    }
    _expectSuccess(response.statusCode, body);
    if (body.isEmpty) return <String, dynamic>{};
    return json.decode(body) as Map<String, dynamic>;
  }

  void _expectSuccess(int status, String body) {
    if (status >= 200 && status < 300) return;
    String message = 'Une erreur est survenue. Réessayez.';
    try {
      final decoded = json.decode(body) as Map<String, dynamic>;
      final detail = decoded['detail'];
      if (detail is String && detail.isNotEmpty) message = detail;
    } catch (_) {
      // Corps non JSON (ex. 429 en texte brut).
      if (status == 429) {
        message = 'Trop de tentatives. Patientez une minute.';
      }
    }
    throw ApiException(status, message);
  }

  /// Tente un rafraîchissement du jeton d'accès avec le refresh token.
  Future<bool> tryRefresh() async {
    final refresh = _refreshToken;
    if (refresh == null) return false;
    try {
      final client = HttpClient();
      final request = await client.postUrl(
        Uri.parse('${ApiConfig.apiBase}/auth/refresh'),
      );
      request.headers.contentType = ContentType.json;
      request.write(json.encode({'refresh_token': refresh}));
      final response = await request.close().timeout(_timeout);
      final body = await utf8.decoder.bind(response).join();
      if (response.statusCode != 200) return false;
      final data = json.decode(body) as Map<String, dynamic>;
      setTokens(
        accessToken: data['access_token'] as String,
        refreshToken: (data['refresh_token'] as String?) ?? refresh,
      );
      return true;
    } catch (_) {
      return false;
    }
  }

  // -------------------------------------------------------------- endpoints

  Future<T> _call<T>(
    Future<T> Function() fn, {
    bool retried = false,
  }) async {
    try {
      return await fn();
    } on _RetryAfterRefresh {
      if (retried) rethrow;
      return _call<T>(fn, retried: true);
    } on SocketException {
      throw ApiException(0, 'Connexion impossible. Vérifiez votre réseau.');
    } on TimeoutException {
      throw ApiException(0, 'Le serveur met trop de temps à répondre.');
    }
  }

  Future<Map<String, dynamic>> getJson(String path) => _call(() async {
        final response = await _request('GET', path);
        return _send(response);
      });

  /// GET renvoyant un tableau JSON (ex. GET /discover).
  Future<List<dynamic>> getList(String path) => _call(() async {
        final response = await _request('GET', path);
        final res = await response.close().timeout(_timeout);
        final body = await utf8.decoder.bind(res).join();
        if (res.statusCode == 401 && await tryRefresh()) {
          throw _RetryAfterRefresh();
        }
        _expectSuccess(res.statusCode, body);
        if (body.isEmpty) return <dynamic>[];
        return json.decode(body) as List<dynamic>;
      });

  Future<Map<String, dynamic>> postJson(
    String path,
    Map<String, dynamic> payload,
  ) =>
      _call(() async {
        final request = await _request('POST', path);
        request.headers.contentType = ContentType.json;
        request.write(json.encode(payload));
        return _send(request);
      });

  Future<Map<String, dynamic>> putJson(
    String path,
    Map<String, dynamic> payload,
  ) =>
      _call(() async {
        final request = await _request('PUT', path);
        request.headers.contentType = ContentType.json;
        request.write(json.encode(payload));
        return _send(request);
      });

  Future<Map<String, dynamic>> deleteJson(String path) => _call(() async {
        final request = await _request('DELETE', path);
        return _send(request);
      });

  /// Upload d'une photo de profil (multipart/form-data, champ `file`).
  Future<Map<String, dynamic>> postPhoto(
    String path,
    List<int> bytes, {
    String filename = 'photo.jpg',
  }) =>
      _call(() async {
        final boundary = 'faso-${DateTime.now().millisecondsSinceEpoch}';
        final request = await _request('POST', path);
        request.headers.contentType = MediaType(
          'multipart',
          'form-data',
          parameters: {'boundary': boundary},
        );
        final head = utf8.encode(
          '--$boundary\r\n'
          'Content-Disposition: form-data; name="file"; filename="$filename"\r\n'
          'Content-Type: image/jpeg\r\n\r\n',
        );
        final tail = utf8.encode('\r\n--$boundary--\r\n');
        request.contentLength = head.length + bytes.length + tail.length;
        request.add(head);
        request.add(bytes);
        request.add(tail);
        return _send(request);
      });
}

/// Signal interne : jeton rafraîchi, rejouer la requête une fois.
class _RetryAfterRefresh implements Exception {}
