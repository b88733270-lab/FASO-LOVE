/// Socle multi-plateforme du client HTTP FASO LOVE.
///
/// Toute la logique (jetons, endpoints, rejeu sur 401, erreurs FR) vit ici ;
/// seul le TRANSPORT diffère (mobile/desktop : dart:io · web : dart:html) —
/// voir `api_client_io.dart` / `api_client_web.dart` / `api_client_stub.dart`.
library;

import 'dart:async';
import 'dart:convert';

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

/// Erreur transport générique (perte réseau) — indépendante de dart:io
/// pour rester compilable sur le web.
class ApiNetworkException implements Exception {}

/// Réponse brute renvoyée par un transport.
typedef RawResponse = ({int status, String body});

/// Socle du client : gestion des jetons + endpoints + politique 401.
abstract class ApiClientCore {
  String? accessToken;
  String? refreshToken;

  static const Duration timeout = Duration(seconds: 20);

  bool get hasSession => accessToken != null;

  void setTokens({required String accessToken, required String refreshToken}) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
  }

  void clearTokens() {
    accessToken = null;
    refreshToken = null;
  }

  // ------------------------------------------------ transport (plateforme)

  /// Exécute une requête HTTP et renvoie (status, body).
  ///
  /// - [payload] : corps JSON encodé (null = pas de corps) ;
  /// - [photoBytes]/[photoName] : upload multipart du champ `file`.
  ///
  /// Implémentation fournie par la plateforme (io/web) ; DOIT lever
  /// [ApiNetworkException] en cas de perte réseau.
  Future<RawResponse> rawRequest(
    String method,
    String path, {
    Map<String, dynamic>? payload,
    List<int>? photoBytes,
    String? photoName,
  });

  // -------------------------------------------------- mécaniques internes

  void expectSuccess(int status, String body) {
    if (status >= 200 && status < 300) return;
    String message = 'Une erreur est survenue. Réessayez.';
    try {
      final decoded = json.decode(body) as Map<String, dynamic>;
      final detail = decoded['detail'];
      if (detail is String && detail.isNotEmpty) message = detail;
    } catch (_) {
      if (status == 429) {
        message = 'Trop de tentatives. Patientez une minute.';
      }
    }
    throw ApiException(status, message);
  }

  /// Tente un rafraîchissement du jeton d'accès avec le refresh token.
  Future<bool> tryRefresh() async {
    final refresh = refreshToken;
    if (refresh == null) return false;
    try {
      final res = await rawRequest(
        'POST',
        '/auth/refresh',
        payload: {'refresh_token': refresh},
      );
      if (res.status != 200 || res.body.isEmpty) return false;
      final data = json.decode(res.body) as Map<String, dynamic>;
      setTokens(
        accessToken: data['access_token'] as String,
        refreshToken: (data['refresh_token'] as String?) ?? refresh,
      );
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Enrobe un appel : rejeu unique après refresh 401 + traduction d'erreurs.
  Future<T> guarded<T>(
    Future<T> Function() fn, {
    bool retried = false,
  }) async {
    try {
      return await fn();
    } on RetryAfterRefresh {
      if (retried) rethrow;
      return guarded<T>(fn, retried: true);
    } on ApiNetworkException {
      throw ApiException(0, 'Connexion impossible. Vérifiez votre réseau.');
    } on TimeoutException {
      throw ApiException(0, 'Le serveur met trop de temps à répondre.');
    }
  }

  Future<dynamic> _decoded(
    String method,
    String path, {
    Map<String, dynamic>? payload,
  }) async {
    final res = await rawRequest(method, path, payload: payload)
        .timeout(timeout);
    if (res.status == 401 && await tryRefresh()) {
      throw RetryAfterRefresh();
    }
    expectSuccess(res.status, res.body);
    if (res.body.isEmpty) return <String, dynamic>{};
    return json.decode(res.body);
  }

  // -------------------------------------------------------------- endpoints

  Future<Map<String, dynamic>> getJson(String path) => guarded(() async {
        return (await _decoded('GET', path)) as Map<String, dynamic>;
      });

  /// GET renvoyant un tableau JSON (ex. GET /discover).
  Future<List<dynamic>> getList(String path) => guarded(() async {
        return (await _decoded('GET', path)) as List<dynamic>;
      });

  Future<Map<String, dynamic>> postJson(
    String path,
    Map<String, dynamic> payload,
  ) =>
      guarded(() async {
        return (await _decoded('POST', path, payload: payload))
            as Map<String, dynamic>;
      });

  Future<Map<String, dynamic>> putJson(
    String path,
    Map<String, dynamic> payload,
  ) =>
      guarded(() async {
        return (await _decoded('PUT', path, payload: payload))
            as Map<String, dynamic>;
      });

  Future<Map<String, dynamic>> patchJson(
    String path,
    Map<String, dynamic> payload,
  ) =>
      guarded(() async {
        return (await _decoded('PATCH', path, payload: payload))
            as Map<String, dynamic>;
      });

  Future<Map<String, dynamic>> deleteJson(String path) => guarded(() async {
        return (await _decoded('DELETE', path)) as Map<String, dynamic>;
      });

  /// Upload d'une photo de profil (multipart, champ `file`).
  Future<Map<String, dynamic>> postPhoto(
    String path,
    List<int> bytes, {
    String filename = 'photo.jpg',
  }) =>
      guarded(() async {
        final res = await rawRequest(
          'POST',
          path,
          photoBytes: bytes,
          photoName: filename,
        ).timeout(timeout);
        if (res.status == 401 && await tryRefresh()) {
          throw RetryAfterRefresh();
        }
        expectSuccess(res.status, res.body);
        if (res.body.isEmpty) return <String, dynamic>{};
        return json.decode(res.body) as Map<String, dynamic>;
      });
}

/// Signal interne : jeton rafraîchi, rejouer la requête une fois.
class RetryAfterRefresh implements Exception {}

/// URL de l'API exposée aux implémentations transport.
String apiEndpoint(String path) => '${ApiConfig.apiBase}$path';
