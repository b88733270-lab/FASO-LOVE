/// Transport **web** du client API (dart:html HttpRequest).
///
/// Sélectionné automatiquement par `api_client.dart` (import conditionnel).
/// Nécessaire à la console d'administration Flutter Web : `dart:io` n'existe
/// pas sur le web.
library;

import 'dart:async';
import 'dart:convert';
import 'dart:html' as html;

import 'api_client_base.dart';

/// Client HTTP FASO LOVE — transport navigateur (XHR), mêmes garanties
/// que la version mobile (Bearer auto, refresh + rejeu, erreurs FR).
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
    final completer = Completer<RawResponse>();
    final xhr = html.HttpRequest()
      ..open(method, apiEndpoint(path))
      ..timeout = ApiClientCore.timeout.inSeconds.toDouble();

    if (accessToken != null) {
      xhr.setRequestHeader('Authorization', 'Bearer $accessToken');
    }

    void terminer(int status, String body) {
      if (!completer.isCompleted) {
        completer.complete((status: status, body: body));
      }
    }

    xhr.onLoadEnd.listen((_) {
      terminer(xhr.status ?? 0, (xhr.responseText ?? '').toString());
    });
    xhr.onError.listen((_) {
      if (!completer.isCompleted) {
        completer.completeError(ApiNetworkException());
      }
    });
    xhr.onTimeout.listen((_) {
      if (!completer.isCompleted) {
        completer
            .completeError(TimeoutException('timeout', ApiClientCore.timeout));
      }
    });

    try {
      if (photoBytes != null) {
        final form = html.FormData();
        form.appendBlob(
          'file',
          html.Blob([photoBytes], 'image/jpeg'),
          photoName ?? 'photo.jpg',
        );
        xhr.send(form);
      } else if (payload != null) {
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.send(json.encode(payload));
      } else {
        xhr.send();
      }
    } catch (_) {
      if (!completer.isCompleted) {
        completer.completeError(ApiNetworkException());
      }
    }
    return completer.future;
  }
}
