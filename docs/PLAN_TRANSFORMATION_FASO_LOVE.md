# FASO LOVE — Analyse du dépôt & Plan de transformation

> **Produit cible** : FASO LOVE — plateforme de rencontre pour le Burkina Faso
> **Document** : Audit complet + feuille de route (v1.0 — 24 septembre 2025)
> **Code source d'origine** : « SparkMatch » (licence MIT, © 2025 Harendra Prajapati)
>
> ⚠️ **Ce document ne modifie aucun code.** Il constitue l'audit demandé (10 points) et le plan détaillé. L'implémentation se fera étape par étape après validation.

---

## 🚨 DÉCISION CRITIQUE N°1 — Politique d'âge (À TRANCHER AVANT TOUT DÉVELOPPEMENT)

Le brief mentionne comme public : **« adultes ET adolescents »**. Ceci pose un problème majeur qu'il faut traiter honnêtement :

| Risque | Détail |
|---|---|
| **Légal (Burkina Faso)** | Majorité fixée à 18 ans ; le Code pénal et le Code des personnes et de la famille protègent strictement les mineurs. Une plateforme de rencontre **amoureuse** mélangeant adultes et mineurs expose l'exploitant à des poursuites pénales. |
| **App stores** | Google Play et l'App Store exigent un classement 18+/17+ pour les apps de rencontre et **bannissent** les apps de dating qui exposent des mineurs à des adultes. |
| **Sécurité** | Mélanger adultes et adolescents sur une app de rencontre amoureuse crée un risque d'exploitation (grooming) impossible à modérer correctement. |
| **Commercial** | Aucun prestataire de paiement ou d'hébergement sérieux n'acceptera ce risque. |

**Recommandation ferme** :
1. **Option A (recommandée)** : FASO LOVE strictement **18+**, avec vérification d'âge renforcée (date de naissance + garde-fou côté serveur + modération des signalements ; vérification documentaire optionnelle en phase 2).
2. **Option B** : FASO LOVE 18+ **plus tard, un produit séparé** pour les jeunes (réseau d'amitié non romantique, fortement modéré, sans géolocalisation précise) — juridiquement, cela ne peut **pas** être la même application.

👉 *Ce plan suppose l'Option A (18+ strict) sauf décision contraire explicite.*

---

# PARTIE 1 — AUDIT DU DÉPÔT EXISTANT

## ⚠️ Constat central : le README ne correspond pas au code

Le README vend une plateforme complète (FastAPI, PostgreSQL, matching IA, chat temps réel, dashboard admin, « 10 000+ utilisateurs simultanés », éditions Community/Enterprise…). **Rien de tout cela n'existe dans le dépôt.** Le README est un argumentaire commercial de l'auteur original (il propose ses services de développement et des « upgrades payantes »). Ne jamais se fier au README : c'est un **prototype d'interface**, pas un produit.

### Inventaire chiffré

| Élément | Réalité mesurée |
|---|---|
| Fichiers Dart | **127 fichiers dont 108 vides (0 ligne)** — 85 % du code est un squelette vide |
| Code réel | ~2 000 lignes réparties dans 19 fichiers |
| Backend FastAPI | **Aucun** (zéro `.py`, zéro `requirements.txt`, zéro `alembic`) |
| Base de données | **Aucune** (zéro SQL, zéro migration) |
| Tests | 1 seul — et c'est le test « compteur » par défaut de Flutter, **qui échouerait** car il teste un compteur qui n'existe pas |
| Dépendances déclarées | `cupertino_icons`, `font_awesome_flutter`, `provider`, `flutter_lints` — **c'est tout** |
| Dépendances vantées par le README | `flutter_bloc`, `dio`, `socket_io_client`, `cached_network_image` → **aucune n'est utilisée ni déclarée** |
| État git | 1 seul commit (« Update README.md ») |

---

## 1. Architecture Flutter

**Structure** : clean architecture nominale `core / data / domain / presentation`, mais factice :
- `lib/core/services/` : 7 fichiers sur 8 **vides** (`api_service`, `auth_service`, `dio_client`, `local_storage`, `location_service`, `notification_service`, `storage_service`). Seul `match_service.dart` contient du code (données factices).
- `lib/data/` : 5 providers/repositories sur 6 **vides**. Seul `discover_provider.dart` fonctionne (ChangeNotifier + `provider`).
- `lib/domain/` : **entièrement vide** (entities, use_cases).
- `lib/presentation/` : seuls 6 écrans réels (voir §5-6) + `profile_card` + `action_button`.

**Ce qui tourne réellement** : `main.dart` → `SparkMatchApp` (MaterialApp, rose type Tinder `#FE3C72`) → `HomeScreen` (bottom navigation à 4 onglets : Discover / Matches / Explore / Profile).

**Anomalie majeure** : le dépôt contient les restes d'un **autre projet** de l'auteur — une marketplace de médicaments « HP Medics » (dossiers `vendor/`, `orders/`, `medicine_*`, `cart/`, `payment/`, `admin/vendor_approval`, `AppStrings.appName = "HP Medics"`). Tous ces fichiers sont vides mais polluent l'arborescence et révèlent un copier-coller de template. **À supprimer intégralement en Phase 0.**

## 2. Backend FastAPI

**Inexistant.** Aucun dossier `fastapi_backend`, aucun fichier Python, aucun `.env.example`. Toute la couche serveur est à construire de zéro.

## 3. PostgreSQL & migrations

**Inexistants.** Aucun schéma, aucune migration Alembic, aucune config de connexion. À concevoir entièrement (voir Partie 2, schéma cible).

## 4. Authentification

**Inexistante.** `auth_service.dart`, `auth_provider.dart`, `auth_repository.dart`, `login_screen.dart`, `registration_screen.dart` sont **tous vides**. Seule trace : des chaînes de validation (« Password must be at least 6 characters » — insuffisant, viser 8+ avec règles de complexité) dans `app_strings.dart`. Aucune gestion de token, aucun stockage sécurisé, aucune session.

## 5. Matching

`match_service.dart` (147 lignes) + `discover_provider.dart` (72 lignes) :
- **100 % fictif et local** : génère 10 profils aléatoires (`Random()`) à chaque ouverture — noms américains (Emma, Liam…), bios anglaises, photos Unsplash, âges 18-32, distances **en miles**.
- `likeUser / dislikeUser / superLikeUser` = `print()` après un `Future.delayed` factice. Commentaire dans le code : *« In real app: await apiClient.post(...) »*.
- Aucun algorithme de pertinence, aucun filtre (âge, distance, genre), aucune réciprocité (le concept même de « match » n'existe pas), rien côté serveur.
- Le swipe est un `PageView` + `GestureDetector` basique (pas de cartes empilées façon Tinder).

`matches_screen.dart` affiche **une liste vide en dur** (« No matches yet ») — l'écran grille existe mais n'est jamais alimenté.

## 6. Chat

`message_screen.dart` (130 lignes) : bulles de messages avec **10 messages codés en dur** (`'This is a sample message $index'`), alternance `isMe = index % 2`. Aucun WebSocket, aucune API, aucune persistance, aucun indicateur de lecture/frappe. Le champ de saisie n'envoie rien. L'écran n'est accessible que depuis Explore (non branché sur les Matches).

## 7. Dashboard / Admin

**Inexistant.** `admin_dashboard_screen.dart`, `admin_stats_card.dart`, `user_list_screen.dart`, `user_detail_screen.dart`, `admin_settings_screen.dart`, `pending_vendors_screen.dart`, `vendor_detail_screen.dart` : **tous vides (0 ligne)**. Toute la modération et l'administration sont à construire.

## 8. Tests existants

`test/widget_test.dart` (31 lignes) : le **test « compteur » généré automatiquement** par `flutter create`. Il recherche un texte « 0 » et une icône `+` qui n'existent pas dans `HomeScreen` → **échouerait si exécuté**. Couverture réelle : **0 %**. Aucune CI pour les exécuter de toute façon.

## 9. Problèmes de sécurité identifiés

| # | Gravité | Problème |
|---|---|---|
| S1 | 🔴 Critique | **Photos de personnes réelles** dans `assets/images/` (`profile1/2/3.jpeg` : selfies de vraies jeunes femmes, probablement récupérés en ligne). Usage commercial sans consentement = risque juridique (droit à l'image) + éthique. **Suppression impérative en Phase 0.** |
| S2 | 🔴 Critique | Photos de profils servies depuis des **URL Unsplash publiques** présentées comme des utilisateurs — interdit en production (fausse représentation + conditions Unsplash). |
| S3 | 🔴 Critique | Aucune authentification, aucun contrôle d'accès, aucune vérification d'âge. |
| S4 | 🟠 Élevé | Aucune donnée chiffrée : pas de `flutter_secure_storage`, pas de TLS pinning, pas de politique de mots de passe sérieuse (min 6). |
| S5 | 🟠 Élevé | Identifiants Android par défaut : `applicationId = com.example.dating_app`, label `dating_app`, icône Flutter par défaut. Nom de package Dart générique `dating_app`. |
| S6 | 🟠 Élevé | Aucune mention de consentement, CGU, politique de confidentialité — **obligatoires** (loi burkinabè n°010-2017/AN sur la protection des données personnelles, contrôlée par la CIL ; et exigences des stores). |
| S7 | 🟡 Moyen | Pas de mécanisme de signalement/blocage, sans lequel une app de rencontre est refusée par les stores. |
| S8 | 🟡 Moyen | `print()` dans le code métier (fuite de données en logs), aucune gestion d'erreurs normalisée. |

## 10. Ce qui manque pour une vraie production

Tout : backend, BDD, auth, chat réel, notifications push, stockage de médias, modération, dashboard admin, tests, CI/CD, monitoring/crash reporting, i18n (tout est en anglais), gestion hors-ligne (connexions 2G/3G au Burkina), compression d'images, optimisation données mobiles, configuration de release (icônes, splash, keystore, ProGuard), conformité légale (CIL/CGU), paiements.

## 11. Licences & conformité (exigence du brief)

| Élément | Licence / statut | Action |
|---|---|---|
| Code « SparkMatch » | MIT, © 2025 Harendra Prajapati | ✅ Usage commercial autorisé. **Conserver `LICENSE` tel quel** + ajouter un fichier `NOTICE` (ou section « Crédits » dans l'app) mentionnant l'origine. Ne jamais retirer la notice. |
| `provider`, `cupertino_icons` | MIT | ✅ Compatibles production |
| `font_awesome_flutter` | MIT (code) ; icônes Font Awesome Free sous CC-BY 4.0 | ✅ Compatible ; attention à l'attribution si usage d'icônes FA |
| Photos Unsplash (URLs) | Licence Unsplash | ⚠️ OK techniquement, **interdit de les présenter comme des utilisateurs** ; à retirer |
| `assets/images/profile*.jpeg` | **Inconnue — photos de personnes réelles** | 🔴 **À supprimer impérativement** (droit à l'image, aucun consentement) |
| Branding « SparkMatch » / « HP Medics » / couleur rose #FE3C72 (≈ Tinder) | Noms de l'auteur original / couleur trop proche d'une marque connue | 🔴 Ne pas réutiliser : nouvelle identité FASO LOVE (logo, palette propres) |
| Nom `dating_app` / `com.example.dating_app` | — | À renommer : `faso_love` / `bf.fasolove.app` (à réserver) |

---

# PARTIE 2 — PLAN DE TRANSFORMATION

## A. Architecture cible

```
faso-love/                         (monorepo ou 2 dépôts — à décider)
├── app/                           Flutter (iOS, Android, puis Web léger)
│   └── lib/
│       ├── core/                  constantes, thème FASO LOVE, utils, DI, erreurs
│       ├── data/                  datasources (API, WS, local sécurisé), models, repos
│       ├── domain/                entities, usecases, contrats de repos
│       ├── presentation/          BLoC/Cubit par feature + écrans
│       └── l10n/                  fr (défaut) + mooré + dioula + fulfuldé (phase ult.)
├── backend/                       FastAPI (Python 3.11+), architecture modulaire
│   ├── app/
│   │   ├── modules/               auth, users, profiles, media, matching,
│   │   │                          chat, reports, moderation, billing, admin
│   │   ├── core/                  config, sécurité (JWT argon2), deps, logging
│   │   └── main.py
│   ├── alembic/                   migrations versionnées
│   └── tests/                     pytest + httpx (cible ≥ 80 % sur modules cœur)
├── admin/                         Dashboard (voir question ouverte Q2)
├── infra/                         docker-compose, reverse proxy (Caddy/Traefik), scripts
└── docs/                          ce plan, ADR, runbooks
```

**Stack technique recommandée**

| Couche | Choix recommandé | Justification Burkina Faso |
|---|---|---|
| App mobile | Flutter 3.x stable, **flutter_bloc** (ou Riverpod), `dio` (rétries/timeout), `web_socket_channel`, `flutter_secure_storage`, `geolocator`, `cached_network_image`, `image_picker` + compression, `firebase_messaging` | Une seule codebase iOS+Android ; compression d'images et cache agressif pour réseaux 2G/3G coûteux |
| API | **FastAPI** (async) + Pydantic v2 + SQLAlchemy 2 (async) + Alembic | Conforme au brief ; excellent avec PostgreSQL async |
| BDD | **PostgreSQL 16 + PostGIS** | Recherche géographique performante (matching par distance à Ouagadougou, Bobo-Dioulasso…) |
| Temps réel | WebSocket natif FastAPI + **Redis** (pub/sub, présence, cache, rate-limit) | Chat + statut « en ligne » |
| Tâches async | Redis Queue / Celery : modération d'images, e-mails/SMS, recalculs de matching | Découple les opérations lentes |
| Médias | Stockage objet compatible S3 (MinIO auto-hébergé ou Scaleway/Backblaze) + CDN ; upload signé | Photos compressées WebP, tailles multiples |
| Notifications | Firebase Cloud Messaging (gratuit, fiable sur Android dominants) | Android = part de marché écrasante en Afrique de l'Ouest |
| Auth | JWT courte durée + refresh, **OTP SMS** (numéro burkinabè +226) comme preuve principale | Faible usage e-mail ; téléphone = identité |
| Dashboard admin | **Option 1** : Flutter Web (même codebase) / **Option 2** : Next.js + shadcn | Voir question Q2 |
| Paiements | **Orange Money + Moov Money** (agrégateurs : PayDunya, LigdiCash, CinetPay) ; Stripe en complément diaspora | Cartes bancaires quasi absentes du BF |
| Observabilité | Sentry (crash app + erreurs API), logs structurés JSON, Prometheus/Grafana plus tard | Détection précoce des pannes |
| Sécurité API | HTTPS obligatoire, rate-limiting (SlowAPI), CORS strict, validation Pydantic, argon2, uploads antivirus/modération | — |

**Principes transverses** : offline-tolerant (file d'attente d'actions, retry), compression systématique des images (max ~200 Ko), pagination partout, distances en **kilomètres**, français par défaut.

## B. Fonctionnalités à CONSERVER (du code existant)

| Élément | État | Décision |
|---|---|---|
| Concept des 4 onglets Discover / Matches / Explore / Profile | UI fonctionnelle | ✅ Conserver la navigation, refondre le style |
| `profile_card.dart` + `action_button.dart` | Base visuelle correcte | ✅ Conserver comme point de départ, rebrand + multi-photos |
| `explore_screen.dart` (grille + filtres) | UI seule, données factices | ✅ Conserver le layout, brancher sur API réelle |
| `matches_screen.dart` (grille + empty state) | UI seule | ✅ Idem |
| Structure clean architecture `core/data/domain/presentation` | Coquille | ✅ Conserver l'arborescence, remplir les 108 fichiers vides ou les supprimer |
| `User.fromJson` / modèle simple | Minimal | ⚠️ Conserver le principe, réécrire le modèle complet |
| Licence MIT + `LICENSE` | Conforme | ✅ **Conserver obligatoirement**, + `NOTICE` de crédits |

## C. Fonctionnalités à MODIFIER / REMPLACER

| Élément | Action |
|---|---|
| Branding « SparkMatch » (titres, couleur rose #FE3C72) | 🔁 Remplacer par identité **FASO LOVE** (nouvelle palette — piste : rouge/vert/doré évoquant le Burkina sans copier le drapeau, typographie propre, logo original) |
| Squelette « HP Medics » (vendor, medicine, cart, orders, payment, admin/vendors, strings associées) | 🗑 **Suppression totale** — code mort d'un autre produit |
| `match_service.dart` (données aléatoires locales) | 🗑 Remplacé par `MatchingRepository` → API (profils réels, filtres, géoloc) |
| `message_screen.dart` (messages en dur) | 🗑 Réécriture complète : chat temps réel WebSocket + persistance PostgreSQL |
| `discover_provider` (Provider) | 🔁 Migrer vers BLoC (`flutter_bloc`) pour cohérence et testabilité |
| Photos Unsplash + `profile*.jpeg` | 🗑 Supprimer ; placeholders vectoriels locaux en attendant de vrais profils |
| Distances en miles, noms US, bios EN | 🔁 Kilomètres, français, contexte burkinabè |
| `pubspec name: dating_app`, `applicationId com.example.dating_app` | 🔁 `faso_love`, `bf.fasolove.app` + icône/splash dédiés |
| `main.dart` (MaterialApp minimal, `print`, pas de routage nommé) | 🔁 Réécriture : DI, routage avec guards auth, thème complet, l10n, Sentry |

## D. Fonctionnalités à AJOUTER (le cœur du produit)

**Compte & confiance**
1. Inscription par **numéro +226 + OTP SMS** (opérateurs Orange/Moov/Telecel), onboarding progressif
2. **Vérification d'âge 18+** (date de naissance vérifiée serveur ; selfie-vérification optionnelle phase 2)
3. Profil riche : multi-photos (jusqu'à 6, modérées), bio, centre d'intérêts localisés (maquis, foutou, musique burkinabè…), ville/quartier, intention (sérieux, amitié, discussion)
4. Vérification de photo (badge « profil vérifié ») — anti-arnaques sentimentales, fléau régional
5. CGU + politique de confidentialité + consentements explicites (conformité loi 010-2017/AN + CIL), suppression de compte et export des données

**Découverte & matching**
6. File de profils géolocalisée (PostGIS, rayon configurable en km), filtres âge/distance/intention
7. Like / Pass / Super-like (quota quotidien freemium), match réciproque, anti-revue des profils déjà votés
8. File anti-fraude : détection de nouveaux comptes en masse, scoring de confiance

**Chat & sécurité**
9. Chat 1-à-1 temps réel (WebSocket), accusés de lecture, « en train d'écrire », envoi d'images modérées
10. **Signalement + blocage** en 2 taps, motifs localisés, file de modération
11. Conseils de sécurité intégrés (premier rendez-vous, ne jamais envoyer d'argent — message anti-arnaque automatique au premier échange)

**Modération & admin**
12. Dashboard admin : KPI (inscrits, actifs, matches, signalements), gestion utilisateurs, file de signalements, modération photos, bannissements, journaux d'audit
13. Modération d'images à l'upload (règles + service de détection de nudité ; validation humaine en file)

**Monétisation (phase 7)**
14. Freemium : limites quotidiennes gratuites ; **FASO LOVE Premium** (likes illimités, voir qui vous a liké, boosts, filtres avancés, mode invisible)
15. Paiement **Mobile Money** (Orange Money, Moov Money via PayDunya/LigdiCash/CinetPay) + Stripe pour la diaspora

**Engagement**
16. Notifications push FCM (match, message, like reçu) + SMS de re-engagement (budget maîtrisé)
17. Mode hors-ligne tolérant, retry automatique, faible consommation data

## E. Risques techniques & mitigation

| Risque | Impact | Mitigation |
|---|---|---|
| 💸 Coût des SMS OTP au Burkina | Coût récurrent par inscription | Agrégateur SMS local compétitif (ex. Africa's Talking couvre le BF), OTP WhatsApp en secours, limitation anti-abus par appareil |
| 📶 Connectivité faible / data chère | Abandon utilisateur | Images ≤ 200 Ko, WebP, cache agressif, requêtes paginées, mode « économie de données » |
| 🎭 Arnaques sentimentales (« brouteurs ») | Destruction de la confiance | Badge vérifié, détection comportementale, message anti-arnaque auto, modération réactive, blocage paiement intra-app |
| ⚖️ Conformité données (loi 010-2017/AN, CIL) | Sanctions, fermeture | Registre des traitements, consentements, hébergement documenté, DPO désigné, suppression/export |
| 💬 Modération en langues locales | Contenus haineux non détectés | Règles FR + lexiques mooré/dioula, modérateurs locaux, signalement communautaire |
| 🔄 Scalabilité WebSocket | Saturation en croissance | Redis pub/sub dès le départ, stateless API derrière load balancer |
| 🏦 Intégration Mobile Money | Agrégateurs parfois instables | Abstraction `PaymentGateway` avec 2 prestataires, réconciliation webhook |
| 📱 Refus des stores (apps dating = scrutin renforcé) | Blocage publication | Signalement/blocage, modération UGC, âge 18+, pages légales, compte démo pour review |
| 👥 Ratio femmes/hommes déséquilibré (classique) | Expérience dégradée | Onboarding équilibré, campagnes ciblées, métriques par genre dès le lancement |
| 🔌 Dépendance Firebase/FCM | Point unique de défaillance | Acceptable au départ ; abstraction `PushService` dans le code |

## F. Dépendances à remplacer / auditer

**À retirer** : `font_awesome_flutter` (remplacer par icônes Material/lucide pour cohérence) — ou conserver si design l'exige (licence OK avec attribution).
**À migrer** : `provider` → `flutter_bloc` (+ `equatable`).
**À ajouter (app)** — toutes licences permissives à re-vérifier au moment de l'ajout : `flutter_bloc`, `dio`, `web_socket_channel`, `flutter_secure_storage`, `shared_preferences`, `geolocator`, `cached_network_image`, `image_picker` + `flutter_image_compress`, `firebase_core`/`firebase_messaging`, `flutter_localizations` + `intl`, `go_router`, `sentry_flutter`, `flutter_svg`, `shimmer`, `package_info_plus`.
**À ajouter (backend)** — audit licence systématique (`pip-licenses`) avant prod : `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic` + `pydantic-settings`, `passlib[argon2]` (ou `argon2-cffi`), `python-jose[cryptography]`, `redis`, `celery` (ou `arq`), `httpx`, `pillow`, `boto3` (S3), `slowapi`, `python-multipart`, `sentry-sdk`, `pytest` + `pytest-asyncio` + `coverage`.
**Assets** : fonts Google Fonts (OFL) uniquement ; icônes Material (Apache 2.0) ; **aucune** photo de personne sans autorisation écrite. Un fichier `docs/LICENSES_AUDIT.md` sera maintenu à chaque ajout.

## G. Étapes de développement (feuille de route)

> Ordre conçu pour obtenir rapidement un produit démontrable, puis durcir jusqu'à la mise en production. Chaque phase se termine par une revue avant de passer à la suivante.

| Phase | Contenu | Livrable |
|---|---|---|
| **0 — Nettoyage & fondations du socle** (≈ 1 sem.) | Suppression squelette HP Medics + photos de personnes réelles + URLs Unsplash ; rebrand complet (nom `faso_love`, palette, strings FR) ; suppression des 108 fichiers vides inutiles ; `NOTICE` de crédits MIT ; CI GitHub Actions (analyse + tests) ; suppression du faux test | Repo propre qui compile, identité FASO LOVE |
| **1 — Backend fondations** (≈ 2 sem.) — ✅ **TERMINEE (24 sept. 2025)** | FastAPI + PostgreSQL + Alembic (users, otp_codes, refresh_tokens) ; auth OTP +226 + JWT/refresh avec rotation & révocation ; règle 18+ serveur ; rate-limiting ; Docker Compose ; **36 tests pytest verts** + E2E vrai PostgreSQL | API auth opérationnelle (`backend/`, serveur démo sur :8000) |
| **1b — SMS réel** (à venir) | Adaptateur `SmsSender` de production (agrégateur couvrant le +226 : Africa's Talking, Orange SMS API) + secrets vault | OTP par vrai SMS |
| **2 — Profils & médias** ✅ **TERMINÉE (24 sept. 2025)** | Modèle profil (genre/orientation/ville/bio/intérêts, géoloc opt-in) ; upload photos backend (Pillow : RGB ≤1600 px, EXIF supprimé, quota 6) + file de modération v1 ; écrans Flutter Profil réel (GET/PUT `/profiles/me`, édition, photos) — *Report : PostGIS (phase avancée), stockage S3/MinIO, upload photo depuis l'app* | Utilisateurs réels avec profils |
| **3 — Matching** ✅ **TERMINÉE (24 sept. 2025)** | `GET /discover` (haversine, orientation réciproque, filtres âge/distance, anti-revue), likes idempotents + matchs réciproques (paire canonique), Discover/Explore/Matches Flutter branchés API + fenêtre « C'est un match ! » | Swipe réel de bout en bout |
| **4 — Chat** ✅ **TERMINÉE (24 sept. 2025)** | WebSocket `/ws/chat` (message/typing/read) + REST historique/lecture ; écran conversation Flutter temps réel (repli REST bas débit), accusés de lecture ✓✓ — *Report : Redis pub/sub (multi-instance), FCM* | Messagerie temps réel |
| **5 — Signalement, blocage, admin v1** ✅ **TERMINÉE (24 sept. 2025)** | Reports (motifs FR dont arnaque/mineur) + blocks symétriques ; API `/admin` (stats, signalements, utilisateurs, modération photos) ; **console d'admin Flutter Web** (`lib/main_admin.dart`, double garde OTP + rôle serveur) ; suppression/export compte — *Report : journaux d'audit persistants* | Outils de modération (exigence stores) |
| **6 — Durcissement sécurité & légal** 🟡 **EN COURS** | ✅ Terminé : en-têtes sécurité, coords masquées, rate-limit OTP paramétrable, [CGU](CGU_FASO_LOVE.md) + [politique de confidentialité](POLITIQUE_CONFIDENTIALITE_FASO_LOVE.md) (brouillons à valider par juriste), audit licences (pillow), suppression/export compte — Reste : HTTPS prod + CORS restreint, secrets vault, registre CIL, validation juridique | Conformité pré-lancement |
| **7 — Monétisation** ✅ **TERMINÉE (25 sept. 2025)** | Quotas freemium (30 likes + 1 super like/jour) ; offres Premium FCFA (7j/30j/3 mois) ; **webhooks idempotents**, checkout idempotent, renouvellement par cumul, simulation sandbox certifiée ; abstraction passerelle (`mock` par défaut, squelette **PayDunya** Orange Money BF + Moov Money BF prêt à clés) ; KPIs admin + écran Premium app — *Report : clés de production PayDunya/compte business, Stripe diaspora (7b)* | Revenus activables |
| **8 — Notifications & engagement** (≈ 1 sem.) | FCM complet, préférences de notif, deep links | Rétention |
| **9 — i18n & polish** (≈ 1,5 sem.) | FR complet, préparation mooré/dioula, onboarding guidé, splash/icônes, perf (profiling), accessibilité | App store-ready |
| **10 — Lancement** (≈ 1,5 sem.) | Tests E2E charge (k6), monitoring Sentry, runbook incident, build release signé, fiches Play Store/App Store + compte démo, plan marketing Ouagadougou/Bobo | **Production v1.0** |

**Estimation globale** : ~17-19 semaines de développement structuré (rythme ajustable ; plusieurs phases peuvent être parallélisées si effort accru).

## H. Décisions validées (24 sept. 2025) ✅

1. **Q1 — Politique d'âge** : ✅ **Option A — 18+ strict**, vérification d'âge côté serveur. *(Phase 1)*
2. **Q2 — Dashboard admin** : ✅ **Flutter Web** (codebase unique). *(Phase 5)*
3. **Q3 — Paiements** : ✅ **Mobile Money d'abord** (Orange Money + Moov Money via agrégateur PayDunya / LigdiCash / CinetPay). *(Phase 7)*
4. **Q4 — Organisation du code** : ✅ **Monorepo** dans ce dépôt (`app/`, `backend/`, `admin/`, `infra/`, `docs/`). *(Phase 0/1 — restructuration progressive lors de l'ajout du backend pour éviter les gros déplacements prématurés)*
5. **Q5 — Identité visuelle** : palette proposée en Phase 0 (terracotta/doré/vert profond, inspirée du Burkina Faso, distincte du rose SparkMatch) — ajustable à tout moment. *(Phase 0)*

---

*Document préparé dans le cadre de la transformation du code open-source « SparkMatch » (MIT, © 2025 Harendra Prajapati) — notice de licence conservée conformément aux termes de la licence.*
