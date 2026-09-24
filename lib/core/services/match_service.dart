import 'dart:math';

import 'package:faso_love/core/constants/assets_path.dart';
import 'package:faso_love/data/models/users/user_model.dart';
import 'package:flutter/foundation.dart';

/// Service de découverte TEMPORAIRE — données de démonstration locales.
///
/// Issue du projet « SparkMatch » (licence MIT) — voir NOTICE.md.
/// Adapté pour FASO LOVE : noms, bios et centres d'intérêt en français,
/// distances en KILOMÈTRES, avatars génériques embarqués (aucune photo
/// distante ni de personne réelle).
///
/// TODO(phase-3) : remplacer par un `MatchingRepository` branché sur
/// l'API FastAPI (`GET /discover`, `POST /likes`, `POST /pass`,
/// `POST /superlikes`) avec pagination, filtres et géolocalisation.
class MatchService {
  static final Random _random = Random();

  static const List<String> _femaleNames = <String>[
    'Aminata',
    'Fatimata',
    'Mariam',
    'Awa',
    'Rasmata',
  ];

  static const List<String> _maleNames = <String>[
    'Idrissa',
    'Souleymane',
    'Aboubacar',
    'Yacouba',
    'Moussa',
  ];

  static const List<String> _bios = <String>[
    'Passionnée de cuisine | Amateure de maquis',
    'Ingénieure | Footballeuse du dimanche',
    'Étudiante en médecine | Lectrice | Yoga',
    'Chef cuisinier | Voyageur | Photographe',
    'Enseignante | Musicienne | Amoureuse de la nature',
    'Entrepreneur | Lecteur | Sportif',
    'Artiste | Danse traditionnelle | Photo',
    'Infirmier | Marathonien | Amateur de thé',
  ];

  static const List<String> _interests = <String>[
    'Cuisine',
    'Voyage',
    'Musique',
    'Tech',
    'Nature',
    'Football',
    'Danse',
    'Cinéma',
    'Lecture',
    'Photo',
    'Sport',
    'Théâtre',
    'Mode',
    'Écriture',
    'Langues',
  ];

  /// Simule le chargement d'une file de 10 profils à découvrir.
  ///
  /// TODO(phase-3) : appeler `GET /discover` avec les filtres utilisateur.
  Future<List<User>> getDiscoverableUsers() async {
    try {
      await Future<void>.delayed(const Duration(seconds: 1)); // latence simulée
      return List<User>.generate(10, (_) => _generateRandomUser());
    } catch (e) {
      return _getFallbackUsers();
    }
  }

  User _generateRandomUser() {
    final bool isFemale = _random.nextBool();
    final String name = isFemale
        ? _femaleNames[_random.nextInt(_femaleNames.length)]
        : _maleNames[_random.nextInt(_maleNames.length)];
    final double distanceKm = 0.5 + _random.nextDouble() * 24.5; // 0,5–25 km

    return User(
      id: _random.nextInt(10000).toString(),
      name: name,
      age: 18 + _random.nextInt(15), // démonstration : 18–32 ans
      photoUrl: AssetsPath
          .placeholderAvatars[_random.nextInt(AssetsPath.placeholderAvatars.length)],
      bio: _bios[_random.nextInt(_bios.length)],
      distance: double.parse(distanceKm.toStringAsFixed(1)),
      interests: _generateRandomInterests(),
    );
  }

  List<String> _generateRandomInterests() {
    final int count = 2 + _random.nextInt(3); // 2 à 4 centres d'intérêt
    final Set<String> interests = <String>{};
    while (interests.length < count) {
      interests.add(_interests[_random.nextInt(_interests.length)]);
    }
    return interests.toList();
  }

  List<User> _getFallbackUsers() {
    return <User>[
      User(
        id: 'fallback1',
        name: 'Kadiatou',
        age: 27,
        photoUrl: AssetsPath.avatar1,
        bio: 'Couturière | Amoureuse du Faso Dan Fani',
        distance: 3.2,
        interests: const <String>['Mode', 'Cuisine', 'Voyage'],
      ),
      User(
        id: 'fallback2',
        name: 'Boureima',
        age: 25,
        photoUrl: AssetsPath.avatar4,
        bio: 'Étudiant | Mélomane | Ouaga',
        distance: 1.5,
        interests: const <String>['Musique', 'Cinéma', 'Danse'],
      ),
    ];
  }

  /// TODO(phase-3) : `POST /likes {targetUserId}` + détection du match réciproque.
  Future<void> likeUser(String userId) async {
    await Future<void>.delayed(const Duration(milliseconds: 300));
    debugPrint('Like envoyé (démo) → utilisateur $userId');
  }

  /// TODO(phase-3) : `POST /pass {targetUserId}` (ne plus re-présenter ce profil).
  Future<void> dislikeUser(String userId) async {
    await Future<void>.delayed(const Duration(milliseconds: 300));
    debugPrint('Pass envoyé (démo) → utilisateur $userId');
  }

  /// TODO(phase-3) : `POST /superlikes {targetUserId}` (quota freemium côté serveur).
  Future<void> superLikeUser(String userId) async {
    await Future<void>.delayed(const Duration(milliseconds: 300));
    debugPrint('Coup de cœur envoyé (démo) → utilisateur $userId');
  }
}
