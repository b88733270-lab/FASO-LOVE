/// Transport **mobile/desktop** du client API (dart:io).
///
/// Sélectionné automatiquement par `api_client.dart` (import conditionnel).
library;

import 'dart:convert';
import 'dart:io';

import 'api_client_base.dart';

/// Client HTTP FASO LOVE — sans dépendance externe (dart:io natif).
///
/// - Bearer token injecté automatiquement ;
/// - rafraîchissement automatique du jeton d'accès (1 seule reprise) ;
/// - upload multipart manuel pour les photos de profil ;
/// - WebSocket natif pour le chat temps réel (voir message_screen).
class ApiClient extends ApiClientCore {
  ApiClient._();

  static final ApiClient instance = ApiClient._();

  @override
  Future<RawResponse> rawRequest(
    String method,
    String path, {
    Map<String, dynamic>? payload,
    List<int>? photoBytes,
    String? photoName,
  }) async {
    try {
      final client = HttpClient()
        ..connectionTimeout = ApiClientCore.timeout;
      final request = await client.openUrl(method, Uri.parse(apiEndpoint(path)));
      if (accessToken != null) {
        request.headers.set(
          HttpHeaders.authorizationHeader,
          'Bearer $accessToken',
        );
      }
      if (photoBytes != null) {
        final boundary = 'faso-${DateTime.now().millisecondsSinceEpoch}';
        request.headers.contentType = MediaType(
          'multipart',
          'form-data',
          parameters: {'boundary': boundary},
        );
        final head = utf8.encode(
          '--$boundary\r\n'
          'Content-Disposition: form-data; name="file"; '
          'filename="${photoName ?? 'photo.jpg'}"\r\n'
          'Content-Type: image/jpeg\r\n\r\n',
        );
        final tail = utf8.encode('\r\n--$boundary--\r\n');
        request.contentLength = head.length + photoBytes.length + tail.length;
        request.add(head);
        request.add(photoBytes);
        request.add(tail);
      } else if (payload != null) {
        request.headers.contentType = ContentType.json;
        request.write(json.encode(payload));
      }
      final response = await request.close().timeout(ApiClientCore.timeout);
      final body = await utf8.decoder.bind(response).join();
      return (status: response.statusCode, body: body);
    } on SocketException {
      throw ApiNetworkException();
    }
  }
}
