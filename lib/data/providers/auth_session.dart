import 'package:flutter/foundation.dart';

import '../../core/network/api_client.dart';

/// Session d'authentification FASO LOVE (OTP SMS +226, règle 18+).
///
/// Machine à états :
/// `saisieNumero` → `saisieCode` → (nouveau compte : `saisieNaissance`) →
/// `connecte`.
///
/// Les messages d'erreur proviennent de l'API et sont déjà en français.
class AuthSession extends ChangeNotifier {
  final ApiClient _api = ApiClient.instance;

  static const String _etapeNumero = 'saisie_numero';
  static const String _etapeCode = 'saisie_code';
  static const String _etapeNaissance = 'saisie_naissance';
  static const String _etapeConnecte = 'connecte';

  String _etape = _etapeNumero;
  bool _occupe = false;
  String? _erreur;

  String _telephone = '+226';
  String _code = '';

  /// Code OTP renvoyé en clair en mode DÉMO (OTP_DEV_ECHO) — l'utilisateur
  /// n'a pas besoin de SMS pour essayer l'app dans la preview.
  String? codeDev;

  /// Profil de l'utilisateur connecté (récupéré via GET /auth/me).
  String? myUserId;
  String? myPhone;

  String get etape => _etape;
  bool get occupe => _occupe;
  String? get erreur => _erreur;
  String get telephone => _telephone;
  bool get estConnecte => _etape == _etapeConnecte && _api.hasSession;
  bool get attendDateNaissance => _etape == _etapeNaissance;

  void _definir({String? etape, String? erreur, bool? occupe}) {
    if (etape != null) _etape = etape;
    _erreur = erreur;
    if (occupe != null) _occupe = occupe;
    notifyListeners();
  }

  void retourNumero() {
    _code = '';
    _definir(etape: _etapeNumero, erreur: null);
  }

  /// Étape 1 — demande l'envoi du code SMS.
  Future<void> demanderCode(String numero) async {
    if (_occupe) return;
    _definir(occupe: true, erreur: null);
    try {
      final reponse = await _api.postJson(
        '/auth/otp/request',
        {'phone': numero.trim()},
      );
      _telephone = numero.trim();
      codeDev = reponse['dev_code'] as String?;
      _definir(etape: _etapeCode, erreur: null, occupe: false);
    } on ApiException catch (e) {
      _definir(erreur: e.message, occupe: false);
    }
  }

  /// Étape 2 — vérifie le code. [dateNaissance] (AAAA-MM-JJ) est exigée
  /// uniquement pour une PREMIÈRE connexion (création de compte, règle 18+).
  Future<void> verifierCode(String code, {String? dateNaissance}) async {
    if (_occupe) return;
    _definir(occupe: true, erreur: null);
    try {
      final corps = <String, dynamic>{'phone': _telephone, 'code': code.trim()};
      if (dateNaissance != null && dateNaissance.isNotEmpty) {
        corps['birthdate'] = dateNaissance;
      }
      final tokens = await _api.postJson('/auth/otp/verify', corps);
      _code = code;
      _api.setTokens(
        accessToken: tokens['access_token'] as String,
        refreshToken: tokens['refresh_token'] as String,
      );
      await _chargerMoi();
      _definir(etape: _etapeConnecte, occupe: false, erreur: null);
    } on ApiException catch (e) {
      if (e.statusCode == 400 &&
          e.message.toLowerCase().contains('naissance')) {
        // Premier compte : on demande la date de naissance (règle 18+).
        _code = code.trim();
        _definir(etape: _etapeNaissance, erreur: null, occupe: false);
      } else {
        _definir(erreur: e.message, occupe: false);
      }
    }
  }

  /// Étape 3 — date de naissance (premier compte uniquement).
  Future<void> confirmerNaissance(String dateNaissance) =>
      verifierCode(_code, dateNaissance: dateNaissance);

  Future<void> _chargerMoi() async {
    final moi = await _api.getJson('/auth/me');
    myUserId = moi['id'] as String?;
    myPhone = moi['phone_e164'] as String?;
  }

  /// Déconnexion propre : révocation côté serveur.
  Future<void> seDeconnecter() async {
    try {
      await _api.postJson('/auth/logout', {});
    } catch (_) {
      // Même sans réseau, on purge localement.
    }
    _api.clearTokens();
    myUserId = null;
    myPhone = null;
    codeDev = null;
    _code = '';
    _definir(etape: _etapeNumero, erreur: null, occupe: false);
  }
}
