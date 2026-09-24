/// Bouchon de transport : aucune plateforme compatible détectée
/// (ni `dart:io`, ni `dart:html`). Ne devrait jamais être sélectionné.
library;

import 'api_client_base.dart';

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
  }) {
    throw UnsupportedError(
      'Transport HTTP non disponible sur cette plateforme.',
    );
  }
}
