# FASO LOVE API

Backend **FastAPI** de la plateforme de rencontre FASO LOVE (Burkina Faso, **18+ strict**).

> Phase 1 du [plan de transformation](../docs/PLAN_TRANSFORMATION_FASO_LOVE.md) :
> fondations — auth par numéro de téléphone **+226 + OTP SMS**, vérification
> d'âge **côté serveur**, sessions JWT (access + refresh avec **rotation et
> révocation**), limitation de débit, PostgreSQL + migrations Alembic.

## Démarrage rapide (local, sans Docker)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # adapter si besoin

# Base PostgreSQL seule (option) :
docker compose up -d db

uvicorn app.main:app --reload
# → API : http://localhost:8000  |  Docs : http://localhost:8000/docs
```

En mode dev (`SMS_PROVIDER=console` + `OTP_DEV_ECHO=true`), le code OTP est
affiché dans les logs **et** renvoyé dans le champ `dev_code` de la réponse —
aucun SMS réel n'est envoyé. ⚠️ Désactiver `OTP_DEV_ECHO` hors dev.

## Avec Docker (PostgreSQL + API)

```bash
cd backend
docker compose up --build
```

Les migrations Alembic sont appliquées automatiquement au démarrage de l'API.

## Tests

```bash
cd backend
pytest -v
```

Les tests tournent sur SQLite en mémoire (aucune infrastructure requise) et
couvrent : flux OTP complet (création de compte, reconnexion, usage unique,
verrouillage après N erreurs), **règle 18+**, normalisation des numéros
burkinabè, rotation/révocation des refresh tokens, JWT.

## Endpoints principaux (v1)

### Authentification (Phase 1)
| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/v1/health` | Santé de l'API |
| POST | `/api/v1/auth/otp/request` | Envoie le code OTP par SMS (3/min) |
| POST | `/api/v1/auth/otp/verify` | Vérifie le code → session JWT (+ création de compte, règle 18+) |
| POST | `/api/v1/auth/refresh` | Rotation access/refresh |
| POST | `/api/v1/auth/logout` | Révocation du refresh token |
| GET | `/api/v1/auth/me` | Compte connecté (Bearer) |

### Profils & médias (Phase 2)
| Méthode | Route | Rôle |
|---|---|---|
| PUT / GET | `/api/v1/profiles/me` | Créer/mettre à jour, lire mon profil |
| GET | `/api/v1/profiles/{user_id}` | Profil public (coords jamais divulguées) |
| POST / DELETE | `/api/v1/profiles/me/photos` / `…/{photo_id}` | Upload JPEG (≤10 Mo → RGB ≤1600 px, EXIF supprimé) / suppression |
| GET | `/api/v1/profiles/catalog/interests` | Suggestions de centres d'intérêt FR |

### Matching (Phase 3)
| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/v1/discover?min_age…&max_distance_km=` | File géolocalisée (orientation réciproque, anti-revue) |
| POST | `/api/v1/discover/react` | pass/like/super_like → `{matched, match_id}` |
| GET | `/api/v1/matches` | Matchs + dernier message + non lus |

### Chat (Phase 4)
| Méthode | Route | Rôle |
|---|---|---|
| GET / POST | `/api/v1/matches/{id}/messages` | Historique / envoi REST |
| POST | `/api/v1/matches/{id}/read` | Marquer lu |
| WS | `/api/v1/ws/chat/{match_id}?token=` | Temps réel : `message` / `typing` / `read` |

### Sécurité & compte (Phase 5)
| Méthode | Route | Rôle |
|---|---|---|
| GET / POST / DELETE | `/api/v1/blocks[…/{user_id}]` | Blocage symétrique |
| POST | `/api/v1/reports` | Signalement (arnaque, mineur présumé, …) |
| GET / DELETE | `/api/v1/users/me` → `/users/me/export` + `DELETE /users/me` | Export (portabilité) / suppression intégrale |


### Monétisation (Phase 7)
| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/v1/subscriptions/plans` | Catalogue FCFA + portefeuilles actifs + quotas gratuits |
| GET | `/api/v1/subscriptions/me` | `is_premium`, fin, quotas du jour |
| POST | `/api/v1/subscriptions/checkout` | Démarre le paiement Mobile Money (idempotent 15 min) |
| GET | `/api/v1/payments/{id}` | Statut de ma transaction |
| POST | `/api/v1/payments/{id}/simulate` | Confirmation sandbox uniquement (`PAYMENTS_SIMULATION_ENABLED`) |
| POST | `/api/v1/payments/webhook/{provider}` | Confirmation prestataire (signature + idempotence, toujours 200) |

Configuration : `PAYMENTS_PROVIDER=mock|paydunya`, clés `PAYDUNYA_*`,
`FREE_LIKES_PER_DAY` (30), `FREE_SUPER_LIKES_PER_DAY` (1).

### Back-office (Phase 5, rôle admin en base)
| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/v1/admin/stats` | KPI (utilisateurs, matchs, signalements) |
| GET / POST | `/api/v1/admin/reports` + `/reports/{id}/resolve` | File de signalements + résolution |
| GET / PATCH | `/api/v1/admin/users` + `/users/{id}` | Recherche + (dés)activation |
| GET / POST | `/api/v1/admin/photos` + `/photos/{id}/moderate` | Modération photos |


## Sécurité — points clés

Phases 2–5 :
- Photos : validation stricte Pillow (pas de fichier arbitraire), redimension
  1600 px, **EXIF/GPS supprimés par construction**, file de modération
  (`MEDIA_AUTO_APPROVE=false` en production) ;
- Découverte : un profil **complet avec ≥ 1 photo approuvée** requis ;
  bloqués cachés dans les deux sens ; réaction sur bloqué → 403 ;
- Chat : messagerie réservée aux matchs (404 sinon), WebSocket authentifié
  par access token (`?token=`), codes de fermeture 4401/4403/4404 ;
- En-têtes : `nosniff`, `DENY`, `Referrer-Policy` — détail FR pour toute
  erreur métier ;
- Suppression de compte : effacement explicite (portable SQLite/PG) de
  toutes les données liées + fichiers photos + révocation des sessions.

Phase 1 :

- Les codes OTP et refresh tokens ne sont **jamais stockés en clair**
  (empreinte SHA-256 contextualisée) ;
- OTP : 5 min de validité, 5 tentatives max, anti-renvoi 60 s, usage unique ;
- Refresh tokens : **rotation à chaque usage** + détection de réutilisation ;
- La règle **18+** est appliquée côté serveur uniquement (jamais côté client) ;
- Limitation de débit sur les endpoints sensibles (slowapi).

## Phase 1b (à venir)

- Adaptateur SMS réel pour le Burkina Faso (Africa's Talking / Orange SMS API)
  derrière la même interface `SmsSender` ;
- Gestion des secrets (vault), CORS restreint, en-têtes de sécurité (phase 6).
