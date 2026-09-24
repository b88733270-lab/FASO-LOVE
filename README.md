# ❤️ FASO LOVE

**Rencontres authentiques au Burkina Faso.**
Application de rencontre **strictement réservée aux adultes (18+)**, pensée pour le contexte burkinabè : français d'abord, Mobile Money, faible consommation de données, sécurité et modération au premier plan.

> ⚠️ **Politique d'âge** : FASO LOVE est interdit aux moins de 18 ans.
> La date de naissance est **vérifiée côté serveur** à l'inscription ;
> tout signalement de mineur est traité en priorité.

---

## 📌 État du projet

Ce dépôt est né du projet open-source **SparkMatch** (licence MIT, © 2025
Harendra Prajapati — voir [LICENSE](LICENSE) et [NOTICE.md](NOTICE.md)).
L'audit initial a montré que le code d'origine était un **prototype
d'interface** (85 % de fichiers vides, aucun backend, données factices).

La transformation complète est pilotée par le document :
➡️ **[docs/PLAN_TRANSFORMATION_FASO_LOVE.md](docs/PLAN_TRANSFORMATION_FASO_LOVE.md)**

| Phase | Contenu | Statut |
|---|---|---|
| **0** | Nettoyage & fondations du socle | ✅ **Terminée** |
| **1** | Backend fondations (FastAPI, PostgreSQL, auth OTP +226, règle 18+) | ✅ **Terminée** |
| **2** | Profils & médias (photos modérées, géoloc opt-in) | ✅ **Terminée** |
| **3** | Matching (géolocalisation, likes réciproques, fenêtre match) | ✅ **Terminée** |
| **4** | Chat temps réel (WebSocket + repli REST bas débit) | ✅ **Terminée** |
| **5** | Signalement, blocage, back-office admin (API + console web) | ✅ **Terminée** |
| 6 | Sécurité & conformité (CGU, confidentialité, CIL) | 🟡 En cours |
| **7** | Monétisation Premium (Mobile Money sandbox certifié) | ✅ **Terminée** |
| **8** | Notifications (cloche in-app + push FCM-ready) | ✅ **Terminée** |
| 9 | i18n, polish, performances | ⬜ |
| 10 | Lancement production v1.0 | ⬜ |

### Phase 8 — Notifications (cloche + push FCM-ready)

- 🔔 **Cloche in-app persistante** : notifications de match (🎉 les deux
  membres) et de message (💬 destinataire, aperçu 80 car.) alimentées par
  les événements métier, **anti-spam par conversation** (deuxième message
  non lu du même match ne ré-empile pas) ;
- 📲 **Push FCM-ready** : abstraction prestataire `log` (sandbox,
  journalisé — parcours igual à la passerelle mock des paiements) /
  `fcm` (clé serveur Firebase en vault ; jetons invalides purgés
  automatiquement). Appareils enregistrés via `POST /devices`
  (idempotent, ré-attribution lors d'un changement de compte sur le même
  téléphone, désenregistrement à la déconnexion) ;
- 🎚 **Préférences utilisateur** (matchs / messages) côté serveur, jamais
  côté client ; badge léger `/notifications/count` (60 s de polling
  doux dans l'app) ;
- 🗂 RGPD : export inclut la cloche, suppression de compte efface
  notifications ET appareils ; KPIs admin (notifications envoyées,
  appareils push) ;
- 🧪 8 tests notifications (79 au total) + 8 vérifs E2E (45 au total).

### Phase 7 — Monétisation Premium Mobile Money (sandbox certifié)

- 💰 **Offres FCFA** : Premium 7 jours (1 500) / 30 jours (3 500) / 3 mois
  (9 000) — avantages honnêtes : likes + super likes **illimités**, badge ;
- 📳 **Parcours Mobile Money réaliste** : checkout idempotent (une seule
  demande USSD, fenêtre 15 min), statut `pending` → `succeeded` via
  **webhook signé et idempotent** (rejeus d'agregateur refusés),
  renouvellement **par cumul de durée** ;
- 🚦 **Quotas FREEMIUM** : 30 likes + 1 super like/jour gratuit, blocage
  403 serveur + invitation Premium dans l'app ;
- 🏦 **Abstraction prestataire** : passerelle `mock` (sandbox certifiée,
  parcours identique au réel) + squelette **PayDunya** (agrégateur couvrant
  Orange Money BF + Moov Money BF) prêt à brancher sur clés ;
- 🧮 **Console admin** : KPIs monétisation (abonnés actifs, paiements
  confirmés, revenus FCFA) ;
- 🗂 Conformité : export RGPD étendu (abonnements + transactions),
  suppression de compte efface aussi la monétisation ;
- 🧪 10 tests monétisation + 8 vérifs E2E (checkout, idempotence requête &
  événement, simulation, quotas, empilement).

### Phases 2–5 (backend + app branchée sur l'API réelle)

- 👤 **Profils** : genre/orientation/ville/bio/centres d'intérêt, géolocalisation
  **opt-in** (seules les distances sont affichées, jamais les coordonnées) ;
- 📸 **Photos** : pipeline Pillow (validation, ≤1600 px, **EXIF/GPS supprimés**,
  quota 6) + **file de modération** (pending/approved/rejected) ;
- 🧭 **Découverte géolocalisée** : haversine, orientation réciproque, filtres
  âge/distance, anti-revue, ex-bloqués exclus ;
- 💞 **Matchs réciproques** (like ↔ like) avec fenêtre 🎉 côté app ;
- 💬 **Chat temps réel** WebSocket (`message`/`typing`/`read`) + historique REST,
  accusés de lecture ✓✓, indicateur de frappe, **repli REST** bas débit ;
- 🛡 **Sécurité** : blocage symétrique, signalement (arnaque, mineur…),
  conseil anti-arnaque permanent dans les conversations ;
- 🧑‍⚖️ **Back-office `/admin`** : statistiques, file de signalements + résolution,
  gestion des utilisateurs (désactivation immédiate), modération photos ;
- 🗂 **Conformité** : suppression de compte intégrale depuis l'app +
  export des données (portabilité) ;
- 📱 **App Flutter branchée** : connexion OTP réelle (numéro → code → 18+),
  découvrir/explorer/matcher/discuter sur l'API, repli hors-ligne maquette ;
- 🧪 **79 tests pytest** + **45 vérifications E2E boîte noire** (HTTP+WS réels
  sur PostgreSQL) — 100 % vertes ;
- 🌱 Seed de démonstration burkinabè (`backend/tools_seed_demo.py`).

### Ce que la Phase 1 a fait

- 🏗 **Backend FastAPI complet** dans [`backend/`](backend/README.md) :
  inscription/connexion par **numéro +226 + code OTP SMS**, **vérification
  d'âge 18+ côté serveur**, sessions JWT access/refresh avec **rotation et
  révocation** (détection de réutilisation), limitation de débit (anti-spam
  OTP), PostgreSQL + **migrations Alembic** versionnées ;
- 🧪 **36 tests pytest** (100 % verts) : flux OTP complet, règle 18+,
  normalisation des numéros burkinabè, rotation/révocation des jetons, JWT ;
- ✅ Vérifié de bout en bout sur **vrai PostgreSQL** (`backend/tools_pgserver_check.py`)
  + serveur de dev clé-en-main (`backend/tools_run_dev_api.py` → API + `/docs`) ;
- 🐳 Docker Compose dev (PostgreSQL 16 + API) + CI : job backend (pytest)
  ajouté à côté du job Flutter.

### Ce que la Phase 0 a fait

- 🗑 Suppression de **108 fichiers vides** et du squelette parasite
  « HP Medics » (marketplace de médicaments) laissé par l'auteur initial ;
- 🔴 Suppression des **photos de personnes réelles** et des URLs Unsplash
  utilisées comme faux profils (risque juridique) — remplacées par des
  **avatars génériques locaux** (silhouettes neutres générées par
  `tools/generate_placeholders.py`) ;
- 🎨 Rebranding complet : nom, palette (terracotta/doré/vert Burkina),
  `bf.fasolove.app`, interface **en français**, distances **en kilomètres** ;
- 🧪 Remplacement du test « compteur » par défaut (en échec) par un vrai
  test de fumée + CI GitHub Actions (`flutter analyze` + `flutter test`) ;
- 📜 Ajout de `NOTICE.md` (crédits MIT conservés) et audit des licences
  (`docs/LICENSES_AUDIT.md`).

## 🚀 Démarrer

### Backend (prérequis : Python 3.11+)

```bash
cd backend
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
./.venv/bin/python tools_run_dev_api.py   # PostgreSQL local + migrations + seed démo + API :8000
```

- Documentation interactive : **http://localhost:8000/docs**
- Comptes de démonstration (OTP affiché en mode démo) :
  `+22670000001` … `+22670000008`, admin `+22670000099`
- Match prêt à l'emploi : Kadiatou (+22670000001) ↔ Idrissa (+22670000005)
- Tests : `./.venv/bin/pytest -q` (79 tests) · E2E boîte noire :
  `./.venv/bin/python tools_e2e_full.py` (45 vérifications)

### Application Flutter (prérequis : Flutter 3.x stable)

```bash
flutter pub get
# Émulateur Android : l'API locale est jointe via 10.0.2.2 (défaut)
flutter run
# Autre cible / serveur distant :
flutter run --dart-define=API_URL=http://VOTRE_API:8000
```

### Console d'administration (Flutter Web)

```bash
flutter pub get
flutter run -d chrome -t lib/main_admin.dart --dart-define=API_URL=http://localhost:8000
# build production : flutter build web -t lib/main_admin.dart --dart-define=API_URL=...
```

Connexion avec le compte admin seed `+22670000099` (OTP démo).
4 panneaux : KPIs temps réel, file de **signalements** (arnaques/mineurs en
tête), gestion des **utilisateurs** (désactivation immédiate), **modération
des photos**. Double garde : OTP + rôle `admin` attribué côté serveur.
Le client HTTP est multi-plateforme (`dart:io` mobile · XHR web).


## 🏗️ Architecture (cible)

- **App** : Flutter (iOS/Android) — clean architecture, migration vers
  BLoC planifiée (Phase 1) ;
- **Backend** : FastAPI + PostgreSQL (+ PostGIS en phase avancée) — opérationnel Phases 1–5 ;
- **Admin** : Flutter Web (Phase 5) ;
- **Infra** : Docker, CI GitHub Actions.

## 🤝 Sécurité & signalement

Signalement et blocage d'utilisateurs (Phase 5), modération des photos,
conseils anti-arnaque intégrés. Toute vulnérabilité doit être signalée en
privé avant divulgation publique.

## 📜 Licence & crédits

- Code d'origine « SparkMatch » : **MIT**, © 2025 Harendra Prajapati
  (notices conservées : [LICENSE](LICENSE), [NOTICE.md](NOTICE.md)) ;
- Modifications FASO LOVE : © 2025 FASO LOVE ;
- Audit des dépendances et assets : [docs/LICENSES_AUDIT.md](docs/LICENSES_AUDIT.md).
