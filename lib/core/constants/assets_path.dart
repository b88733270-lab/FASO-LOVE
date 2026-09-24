/// Chemins des assets embarqués FASO LOVE.
///
/// Les avatars génériques sont des silhouettes neutres générées en interne
/// par `tools/generate_placeholders.py` — volontairement sans visage
/// identifiable. AUCUNE photo de personne réelle ne doit être embarquée
/// sans autorisation écrite (droit à l'image).
class AssetsPath {
  static const String avatar1 = 'assets/placeholders/avatar_1.png';
  static const String avatar2 = 'assets/placeholders/avatar_2.png';
  static const String avatar3 = 'assets/placeholders/avatar_3.png';
  static const String avatar4 = 'assets/placeholders/avatar_4.png';
  static const String avatar5 = 'assets/placeholders/avatar_5.png';
  static const String avatar6 = 'assets/placeholders/avatar_6.png';

  /// Avatars de démonstration utilisés avant le branchement de l'API (phase 3).
  static const List<String> placeholderAvatars = <String>[
    avatar1,
    avatar2,
    avatar3,
    avatar4,
    avatar5,
    avatar6,
  ];
}
