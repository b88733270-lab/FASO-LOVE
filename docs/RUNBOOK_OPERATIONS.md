# Runbook d'exploitation FASO LOVE (Phase 9)

> Consignes opérationnelles — pré-production et production pilote. Tout ce
> qui devait être codé l'est ; le reste relève de l'exécution humaine.

## 1. Variables d'environnement requises (production)

| Variable | Obligatoire | Exemple/Notes |
|---|---|---|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://user:pass@pg-host:5432/fasolove` |
| `JWT_SECRET` | ✅ | 64+ caractères aléatoires (`openssl rand -hex 48`) |
| `JWT_ALGORITHM` | ✅ | `HS256` |
| `CORS_ORIGINS` | ✅ | `https://app.fasolove.bf,https://admin.fasolove.bf` (jamais `*`) |
| `ENV` | ✅ | `prod` → /docs Off, HSTS, alertes au démarrage si configs DEV |
| `SMS_PROVIDER` | ✅ | `africastalking` (addresser BF valide à contractualiser) |
| `AT_USERNAME` / `AT_API_KEY` | ✅ si AT | compte Africa's Talking, sandbox → prod |
| `PAYMENTS_PROVIDER` | ✅ | `paydunya` (production) / `mock` (uniquement démo) |
| `PAYDUNYA_MASTER_KEY` / `_PRIVATE_KEY` / `_PUBLIC_KEY` | ✅ si paydunya | console PayDunya business (compte BF) |
| `PAYDUNYA_MODE` | ✅ | `live` / `test` |
| `PAYMENTS_SIMULATION_ENABLED` | ✅ prod | **`false`** OBLIGATOIRE |
| `PUSH_PROVIDER` | ✅ | `fcm` (production) / `log` (sandbox) |
| `FCM_SERVER_KEY` | ✅ si fcm | console Firebase (projet FASO LOVE) |
| `FREE_LIKES_PER_DAY` / `FREE_SUPER_LIKES_PER_DAY` | optionnel | 30 / 1 par défaut |
| `MEDIA_DIR` | ✅ | `./media` local → S3/MinIO recommandé (Phase 10) |
| `MEDIA_MAX_UPLOAD_MB` | optionnel | 10 |

→ **Au démarrage en `ENV=prod`, l'API journalise un ⚠️ pour chacune de ces
valeurs laissées sur son réglage DEV** (voir `app/main.py`). Surveillez-le.

## 2. Mise en production (ordre)

1. Immatriculation entreprise & mentions légales complétées
   (`docs/MENTIONS_LEGALES.md`) ; CGU/politique v1.0 relues par juriste.
2. Hébergement (VM/Docker postgres 15+, backup offsite) — voir §3.
3. DNS + TLS (Caddy/traefik auto) ; CORS limité aux domaines officiels.
4. Vault de secrets (Vaultwarden/Doppler/1Password) — jamais de clés en git.
5. Premier déploiement : `alembic upgrade head`, seed minimal.
6. Smoke suite : `tools_e2e_full.py` contre l'URL de prod (compte test).
7. Sauvegardes : corriger cron §3 + **tester un restore** (outil fourni).
8. Lancement magasin/console : PayDunya clés live + achat test 100 FCFA.

## 3. Sauvegardes (livré Phase 9 ✅)

```bash
# Manuel immédiat
cd backend && ./.venv/bin/python tools_backup_db.py --keep 30

# Cron quotidien 03:25 (UTC), rotation 30 jours
25 3 * * * cd /opt/fasolove/backend && ./.venv/bin/python tools_backup_db.py --keep 30 >> /var/log/fasolove-backup.log 2>&1

# Restauration (⚠️ DÉFINITIVE)
cd backend && ./.venv/bin/python tools_backup_db.py           # snapshot courant d'abord !
./.venv/bin/python tools_restore_db.py backups/fasolove-YYYYMMDD-HHMMSS.sql.gz --force
# Redémarrer l'API après restauration.

# Certification à la demande (sandbox uniquement !)
./.venv/bin/python tools_e2e_backup.py
```

Le manifeste (`backups/manifest.json`) contient sha256 + effectifs — exécutez
un restore test **hebdomadairement** (mission de continuité). Chiffrer avant
envoi hors site (age/gpg) : `age -r <clé> fasolove-*.sql.gz`.

## 4. Incidents — fiches d'intervention

| Incident | Diagnostic | Action immédiate |
|---|---|---|
| **SMS OTP ne partent plus** | `logs fasolove.sms` + dashboard Africa's Talking ; si solde épuisé → recharge; si l'erreur vient de l'API → regarder la chaîne HTTP côté webhook | Passer `SMS_PROVIDER=console` en URGENCE (comptes créés lisibles dans logs) ou fournir le code manuellement au support (délai court) ; communiquer in-app bannière |
| **Webhooks PayDunya muets** | stats : `payments_succeeded` statique alors que des USSD ont été confirmés ; URL `/payments/webhook/paydunya` inaccessible ? (redémarrage?) | Simuler en sandbox : `payments_simulation_enabled` doit RESTER false en prod ; contacter support PayDunya ; rejouir les IPN en républust (nôtros idempotence gère la reditribution) |
| **Vague d'inscriptions abusives / brute-force OTP** | stats users/jour anormale, 200+ demands OTP/min | resserrer `otp_request_rate_limit` à `20/minute`, aller rapidement à une liste noire IP via WAF, ou couper temporairement countries hors BF via l'edge |
| **Base pleine / très lent** | pg_stat_activity + disque ; archivez sauvegardes offsite | Voilà pg_repack / VACUUM, ajouter disque, purger les logs de 90 jours (rotation auto prévue) |
| **Compte qui abuse ses transactions (chargeback)** | liste transactions `failed` rapproché d'une personne | suspendre compte via console admin (rôle/émission ajoutée Phase 10) ; archiver preuves ; blocage au niveau agrégateur |

## 5. Rotation des secrets

| Secret | Périodicité | Rotation |
|---|---|---|
| `JWT_SECRET` | 90 jours | nouvelle clé → sessions existantes invalidées (ré-auth OTP ; transparency court) |
| Clés PayDunya | suspect de fuite / 180 jours | console PayDunya régénérez → vault |
| Clé Africa's Talking | suspect / 180 jours | régénérer → vault |
| `FCM_SERVER_KEY` | suspect seulement | régénérer console Firebase |

## 6. Métriques de veille (Phase 10 = dashboards)

- users actifs 24 h, matchs créés/jour, messages/jour
- taux de conversion checkout : `payments_succeeded / checkouts`
- revenus FCFA/jour (dans la console admin actuelle)
- notifications push envoyées/jour, appareils actifs
- erreurs API 5xx (journaliser → Phase 10 : Sentry)
