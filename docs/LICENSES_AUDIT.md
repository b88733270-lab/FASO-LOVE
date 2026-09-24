# Audit des licences — FASO LOVE

> Registre tenu à jour **avant chaque mise en production**.
> Règle : aucune photo de personne réelle sans autorisation écrite ;
> police de caractères sous OFL uniquement ; vérification systématique
> (`flutter pub` : licence de chaque package ; backend : `pip-licenses`).

## 1. Code source d'origine

| Élément | Licence / titulaire | Statut |
|---|---|---|
| Code « SparkMatch » (base UI Flutter) | MIT — © 2025 Harendra Prajapati | ✅ Conservée : `LICENSE` intact + `NOTICE.md` |

## 2. Dépendances Dart/Flutter déclarées (pubspec.yaml)

| Package | Licence (pub.dev) | Compatibilité production |
|---|---|---|
| `provider` | MIT | ✅ |
| `cupertino_icons` | MIT | ✅ |
| `font_awesome_flutter` | MIT (code) — icônes Font Awesome Free : CC-BY 4.0 | ✅ Attribution requise pour les icônes FA |
| `flutter_lints` (dev) | BSD-3-Clause | ✅ |
| `flutter_test` (SDK, dev) | BSD-3-Clause | ✅ |
| Icônes Material (SDK) | Apache-2.0 | ✅ |

⚠️ À refaire à chaque `pubspec.yaml` modifié (phases 1 à 9 ajouteront :
`flutter_bloc`, `dio`, `web_socket_channel`, `flutter_secure_storage`,
`geolocator`, `cached_network_image`, `firebase_*`, etc.).

## 3. Assets

| Asset | Origine | Licence / statut | Action |
|---|---|---|---|
| `assets/images/profile1-3.jpeg` | Photos de **personnes réelles** (projet d'origine, origine inconnue) | ❌ Aucun consentement — risque droit à l'image | ✅ **SUPPRIMÉES en Phase 0** |
| URLs Unsplash dans le code (faux profils) | Unsplash | ⚠️ Usage interdit pour simuler de vrais utilisateurs | ✅ **RETIRÉES en Phase 0** |
| `assets/placeholders/avatar_1-6.png` | Générés en interne (`tools/generate_placeholders.py`) | ✅ Propriété FASO LOVE — silhouettes neutres | En place |
| Logo & icônes FASO LOVE | À créer (phase 9) | Doit être original (aucune reprise du branding d'origine) | Planifié |

## 4. Branding

| Élément | Statut |
|---|---|
| Nom « SparkMatch », couleur #FE3C72, squelette « HP Medics » | ✅ Supprimés de l'identité produit (Phase 0) |
| Nom « FASO LOVE », palette terracotta/doré/vert | Identité propre — vérifier la disponibilité de la marque au Burkina Faso (OAPI) avant dépôt |

## 5. Backend (Phases 1–5)

| Package | Licence | Compatibilité production |
|---|---|---|
| `fastapi` | MIT | ✅ |
| `uvicorn[standard]` | BSD-3-Clause | ✅ |
| `sqlalchemy[asyncio]` | MIT | ✅ |
| `alembic` | MIT | ✅ |
| `asyncpg` | Apache-2.0 | ✅ |
| `pydantic` / `pydantic-settings` | MIT | ✅ |
| `pyjwt` | MIT | ✅ |
| `slowapi` | MIT | ✅ |
| `python-multipart` | Apache-2.0 | ✅ |
| `pillow` (traitement photos Phase 2) | HPND (MIT-CMU, permissive) | ✅ |
| `pytest` / `pytest-asyncio` (dev) | MIT / Apache-2.0 | ✅ |
| `httpx` (prod Phase 7 — client agrégateur Mobile Money + dev) | BSD-3-Clause | ✅ |
| `aiosqlite` (dev) | MIT | ✅ |
| `pgserver` (outil local uniquement) | PostgreSQL License | ✅ (hors image prod) |

⚠️ Revérifier avec `pip-licenses` à chaque ajout dans `requirements*.txt`
(notamment phases 8–10 : redis, boto3, celery, firebase-admin/messaging, Sentry…).

**Outils de test uniquement (non embarqués en production) :**
`pytest`, `pytest-asyncio`, `httpx`, `aiosqlite`, `pgserver`,
`websockets` (script E2E boîte noire `tools_e2e_full.py`).
