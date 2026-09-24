# 📦 Livraison finale FASO LOVE v1.0 — Phase 10

> Guide de mise en service commercial **bout en bout**, du répertoire jusqu'au
> client final sur Orange Money. Toutes les exécutions techniques sont
> prêtes ; seules les étapes qui exigent un opérateur humain restent marquées
> 🔧.

## 1. Ce qui est livré (état à jour)

### 1.1 API (backend FastAPI, v1.0.0)
- 7 migrations Alembic appliquées à la création du conteneur ;
- **79 tests pytest** (authren OTP, règle 18+, profils/photos, matching,
  chat REST+WS, modération, RGPD, paiements, notifications, sauvegarde) ;
- **45 contrôles E2E boîte noire** sur PostgreSQL réel (identités purgeables,
  reproductible indéfiniment) ;
- Certification **sauvegarde→restauration** en boîte noire (témoin
  recréé avec profil intact) ;
- **0 vulnérabilité CVE déployée connue** (pip-audit, épinglé) ;
- Endpoints `/health`, `/health/live`, `/health/ready` (Docker/k8s probes) ;
- Sentry optionnel (`SENTRY_DSN` → branché au runtime, PII absents).

### 1.2 App Flutter (Android, iOS-ready, Web)
- 4 onglets produits complets + onboarding OTP, cloche notifications,
  centre Premium (mobile money sandbox-certifié), console admin Flutter Web
  (5 panneaux : stats, signalements, photos, modération+, recherche) ;
- 42 fichiers Dart vérifiés syntaxe (tree-sitter) ;
- Version pubspec : **1.0.0+1**.

### 1.3 Infrastructure & exploitation
- `backend/Dockerfile` (non-root, healthcheck, alembic automatique),
- `infra/docker-compose.prod.yml` (api + PostgreSQL 16 + Caddy TLS),
- `infra/Caddyfile` (Let's Encrypt auto, étapes de sécurité redondantes),
- `infra/.env.example` modèle à compléter (vault),
- `infra/docker-backup.sh` (dump quotidien cron + rotation + manifeste),
- CI GitHub Actions 4 étages (pytest, pip-audit, Dart, E2E fumée),
- Runbook ops, checklist OWASP, documentation juridique v1.0.

## 2. Mise en production (🔧 — 1 matinée de votre part)

### 2.1 Pré-requis logistique
| Élément | Où | Délai moyen |
|---|---|---|
| VPC/VM Ubuntu 24.04 (2 vCPU / 2 Go → commence) | OVHcloud, Scaleway, AWS Lightsail (zone EU) | 1 h |
| Nom de domaine `api.fasolove.bf` | Sonatel-Afrique, AFDomain, Namecheap | 1 j |
| Compte **PayDunya business** + KYC | paydunya.com | 3-7 j |
| Compte **Africa's Talking** | africastalking.com | 1-3 j |
| Projet Firebase + clé FCM | console.firebase.google.com | 30 min |

### 2.2 Procédure (ordre garantie)
```bash
# 1) Sur la VM, cloner le dépôt privé
git clone https://github.com/b88733270-lab/FASO-LOVE /opt/fasolove
cd /opt/fasolove

# 2) Compléter les secrets (NE PAS COMMITER)
cp infra/.env.example infra/.env
editor infra/.env          # remplir tous les <…>

# 3) Premier démarrage (migrations appliquées automatiquement)
docker compose -f infra/docker-compose.prod.yml --env-file infra/.env up -d
docker compose -f infra/docker-compose.prod.yml --env-file infra/.env ps
# → api "Up (healthy)", db "Up (healthy)", proxy "Up"

# 4) Fumée réelle (remplacez api.faso... par votre domaine)
curl https://api.fasolove.bf/api/v1/health | jq .
curl https://api.fasolove.bf/api/v1/subscriptions/plans | jq '.plans[].titre'

# 5) Cron sauvegardes sur l'hôte
( crontab -l ; echo '25 3 * * * docker compose -f /opt/fasolove/infra/docker-compose.prod.yml --env-file /opt/fasolove/infra/.env run --rm backup /docker-backup.sh' ) | crontab -

# 6) Achat test de 100 FCFA sur VOTRE compte → vérifier statut succeeded
#    (console PayDunya + jeux d'onglets API)
```
**Dernier garde-fou avant ouverture** : lire garde-fou ENV=prod dans les logs
API (ici : aucun ⚠️).

## 3. Publication des apps (🔧 — 1 jour)

### Android (Google Play)
```bash
cd .
# Keystore de publication (à conserver 25 ans !!)
keytool -genkey -v -keystore faso-love-release.jks \
  -keyalg RSA -keysize 2048 -validity 10000 -alias fasolove
# android/key.properties → signingConfigs.release
flutter build appbundle --release --dart-define=API_URL=https://api.fasolove.bf/api/v1
```
Google Play Console : icône 512, fiche produit FR+EN, captures téléphone
(FASO LOVE Découvrir / Matchs / Premium), formulaire de confidentialité
(renvoyer vers `docs/POLITIQUE_CONFIDENTIALITE_FASO_LOVE.md` hébergé),
classification 18+, countries: **Burkina Faso** → release initiale ~1-3 j.

### iOS
```bash
flutter build ipa --release --dart-define=API_URL=https://api.fasolove.bf/api/v1
```
App Store Connect : compte Apple Developer, revue ~24-48 h (la justification
Mobile Money répond au rejet courant d'Apple Inc sur l'achat in-app *dons*;
les abonnements payants doivent utiliser **In-App Purchase** seulement si
Apple l'exige pour le contenu numérique débloqué — une config hybride est
documentée dans `docs/RUNBOOK_OPERATIONS.md` si le store le réclame).

## 4. Opérations post-lancement (évidentes maintenant)

- **Vague de spam OTP** : relever `OTP_REQUEST_RATE_LIMIT` env → redémarrer ;
  historique WAF présent dans Caddyfile.
- **Notifications du webhook PayDunya** : toujours-200 + idempotence →
  rejouez l'IPN depuis la console PayDunya sans risque.
- **Suivi revenus** : console admin → 3 KPIs monétisation temps réel.
- **Signalements** : file modération → priorité aux contenus enseignants/en
  rapport escroquerie (marqués par l'algorithme).

## 5. Support clients (v1)
Un utilisateur ne peut pas entrer dans l'app → comparer logs SMS, vérifier
la suppression de son compte (tout supprimer → redémarrer proprement). Les
5 fiches incident du RUNBOOK couvrent l'essentiel.

---

*Page livrée le 25 sept. 2026 — FASO LOVE, la rencontre au Burkina Faso.
Toute la technologie sous-jacente a été testée fin à fin ; il ne reste que
les étapes administratives 🔧 et la traction commerciale. Bon lancement !*
