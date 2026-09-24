/// Chaînes de caractères FASO LOVE (français — langue par défaut).
///
/// L'internationalisation complète (fr + mooré + dioula + fulfuldé) est
/// prévue en phase 9 ; ce fichier centralise déjà les textes visibles.
class AppStrings {
  // Application
  static const String appName = 'FASO LOVE';
  static const String appTagline = 'Rencontres authentiques au Burkina Faso';

  // Navigation
  static const String tabDiscover = 'Découvrir';
  static const String tabMatches = 'Matchs';
  static const String tabExplore = 'Explorer';
  static const String tabProfile = 'Profil';

  // Authentification
  static const String login = 'Connexion';
  static const String register = 'Inscription';
  static const String phoneNumber = 'Numéro de téléphone';
  static const String otpCode = 'Code de vérification';
  static const String email = 'E-mail';
  static const String password = 'Mot de passe';
  static const String confirmPassword = 'Confirmer le mot de passe';
  static const String forgotPassword = 'Mot de passe oublié ?';
  static const String dontHaveAccount = 'Pas encore de compte ? ';
  static const String alreadyHaveAccount = 'Déjà un compte ? ';
  static const String logout = 'Se déconnecter';

  // Messages de validation
  static const String phoneRequired = 'Le numéro de téléphone est requis';
  static const String invalidPhone = 'Veuillez saisir un numéro valide';
  static const String otpRequired = 'Le code de vérification est requis';
  static const String emailRequired = 'L’e-mail est requis';
  static const String invalidEmail = 'Veuillez saisir un e-mail valide';
  static const String passwordRequired = 'Le mot de passe est requis';
  static const String passwordMinLength =
      'Le mot de passe doit contenir au moins 8 caractères';
  static const String passwordsNotMatch =
      'Les mots de passe ne correspondent pas';
  static const String ageRestriction =
      'Vous devez avoir au moins 18 ans pour utiliser FASO LOVE';

  // Découverte
  static const String likeAction = 'Aimer';
  static const String passAction = 'Passer';
  static const String superLikeAction = 'Coup de cœur';
  static const String noMoreProfiles =
      'Plus de profils à découvrir pour le moment';

  // Sécurité & modération
  static const String report = 'Signaler';
  static const String block = 'Bloquer';
  static const String unblock = 'Débloquer';
  static const String reportThanks =
      'Merci pour votre signalement. Notre équipe va l’examiner.';
  static const String safetyTip =
      'Ne partagez jamais d’argent ni vos informations personnelles avec un inconnu.';

  // Premium
  static const String premium = 'FASO LOVE Premium';
  static const String subscribe = 'S’abonner';
  static const String unlimitedLikes = 'Likes illimités';
  static const String seeWhoLikesYou = 'Voir qui vous a aimé';

  // Commun
  static const String send = 'Envoyer';
  static const String submit = 'Valider';
  static const String cancel = 'Annuler';
  static const String save = 'Enregistrer';
  static const String edit = 'Modifier';
  static const String delete = 'Supprimer';
  static const String back = 'Retour';
  static const String next = 'Suivant';
  static const String loading = 'Chargement…';
  static const String noData = 'Aucune donnée disponible';
  static const String errorOccurred = 'Une erreur est survenue';
  static const String tryAgain = 'Réessayer';
  static const String success = 'Succès';

  // Légal
  static const String termsOfUse = 'Conditions d’utilisation';
  static const String privacyPolicy = 'Politique de confidentialité';
  static const String deleteAccount = 'Supprimer mon compte';
}
