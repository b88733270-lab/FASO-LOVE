import 'package:faso_love/core/network/api_client.dart';
import 'package:faso_love/core/services/match_service.dart';
import 'package:faso_love/data/models/users/user_model.dart';
import 'package:flutter/material.dart';

/// File de découverte FASO LOVE — branchée sur l'API réelle
/// (`GET /discover`, `POST /discover/react`).
///
/// En cas d'API injoignable (démo hors-ligne), repli sur les profils
/// locaux de [MatchService] pour garder l'application navigable.
class DiscoverProvider with ChangeNotifier {
  final PageController pageController = PageController();
  final MatchService _fallback = MatchService();
  final ApiClient _api = ApiClient.instance;

  List<User> users = [];
  bool isLoading = true;
  bool horsLigne = false;
  String? erreur;
  int currentIndex = 0;

  /// Rappel déclenché quand un like réciproque crée un match 🎉.
  void Function(User peer)? onMatch;

  DiscoverProvider() {
    recharger();
  }

  Future<void> recharger() async {
    isLoading = true;
    erreur = null;
    notifyListeners();
    try {
      final liste = await _api.getList('/discover?limit=25');
      users = liste
          .map((c) => User.fromDiscoverJson(c as Map<String, dynamic>))
          .toList();
      horsLigne = false;
      currentIndex = 0;
    } on ApiException catch (e) {
      if (e.statusCode == 0) {
        // API injoignable : mode démo hors-ligne.
        users = await _fallback.getDiscoverableUsers();
        horsLigne = true;
        erreur = null;
      } else {
        users = [];
        erreur = e.message;
      }
    } catch (_) {
      users = await _fallback.getDiscoverableUsers();
      horsLigne = true;
    }
    isLoading = false;
    notifyListeners();
  }

  void onPageChanged(int index) {
    currentIndex = index;
    notifyListeners();
  }

  Future<void> swipeLeft() => _reagir('pass');

  Future<void> swipeRight() => _reagir('like');

  Future<void> superLike() => _reagir('super_like');

  Future<void> _reagir(String action) async {
    if (currentIndex >= users.length) return;
    final cible = users[currentIndex];
    bool matched = false;
    if (!horsLigne) {
      try {
        final reponse = await _api.postJson(
          '/discover/react',
          {'target_user_id': cible.id, 'action': action},
        );
        matched = reponse['matched'] == true;
      } on ApiException catch (e) {
        erreur = e.message;
      }
    }
    _goToNextProfile();
    if (matched) {
      onMatch?.call(cible);
    }
  }

  void _goToNextProfile() {
    if (currentIndex < users.length - 1) {
      pageController.nextPage(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    } else if (users.isNotEmpty) {
      users.removeAt(currentIndex);
      notifyListeners();
    }
  }

  @override
  void dispose() {
    pageController.dispose();
    super.dispose();
  }
}
