import 'dart:math';

import 'package:faso_love/core/network/api_client.dart';
import 'package:flutter/foundation.dart';

/// Phase 8 — enregistrement de l'appareil auprès de l'API (push FCM).
///
/// **Mode sandbox (actuel)** : aucun SDK Firebase n'est encore embarqué ;
/// le service génère un jeton local stable « sandbox-<appareil> » et
/// l'enregistre via `POST /devices`. Le parcours serveur (idempotence,
/// préférences, purge des jetons morts) est exactement celui de la Future,
/// production : il suffira de remplacer [_jetonLocal] par le vrai token FCM
/// (`FirebaseMessaging.instance.getToken()`) une fois le projet Firebase
/// branché sur la clé serveur — AUCUN changement côté backend.
class PushService {
  PushService._();
  static final PushService instance = PushService._();

  String? _token;
  bool _enregistre = false;

  /// Jeton d'appareil sandbox : stable pour la durée de la session applicative
  /// (même identité si l'app redémarre l'enregistrement — le serveur est
  /// idempotent de toute façon ; en prod ce sera le token FCM persisté).
  String get _jetonLocal {
    _token ??= 'sandbox-${Random.secure().nextInt(1 << 32).toRadixString(16)}'
        '-${DateTime.now().millisecondsSinceEpoch.toRadixString(16)}';
    return _token!;
  }

  String _plateforme() {
    if (kIsWeb) return 'web';
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return 'android';
      case TargetPlatform.iOS:
        return 'ios';
      default:
        return 'web';
    }
  }

  /// À appeler après connexion (HomeScreen) : enregistre l'appareil une fois
  /// par session. Toutes les erreurs sont silencieuses (le push est un confort,
  /// jamais un prérequis à l'utilisation).
  Future<void> enregistrer() async {
    if (_enregistre) return;
    try {
      await ApiClient.instance.postJson('/devices', {
        'platform': _plateforme(),
        'token': _jetonLocal,
      });
      _enregistre = true;
    } catch (_) {
      // silencieux : nouvelle tentative à la prochaine ouverture.
    }
  }

  /// À appeler à la déconnexion : l'appareil ne doit plus recevoir de push
  /// tant que personne ne s'est reconnecté avec CE téléphone.
  Future<void> desenregistrer() async {
    final token = _token;
    if (token == null) return;
    try {
      await ApiClient.instance.deleteJson('/devices/$token');
    } catch (_) {
      // silencieux
    }
    _enregistre = false;
  }
}
