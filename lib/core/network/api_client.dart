/// Client HTTP FASO LOVE — façade multi-plateforme.
///
/// Importez CE fichier : la bonne implémentation de transport est choisie
/// à la compilation (`dart:io` sur mobile/desktop, XHR sur le web), ce qui
/// permet à la **console d'administration Flutter Web** de partager toute
/// la logique d'authentification et d'endpoints avec l'app mobile.
///
/// Classes exposées : `ApiClient.instance` (singleton), `ApiException`,
/// `ApiClientCore`, `ApiNetworkException`.
library;

export 'api_client_base.dart'
    show
        ApiClientCore,
        ApiException,
        ApiNetworkException,
        RetryAfterRefresh;
export 'api_client_stub.dart'
    if (dart.library.io) 'api_client_io.dart'
    if (dart.library.html) 'api_client_web.dart';
