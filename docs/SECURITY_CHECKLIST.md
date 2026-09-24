# Checklist sécurité de lancement — FASO LOVE (Phase 9)

> À cocher avant tout passage en production. Chaque ligne renvoie à la
> mesure concrète implémentée dans le code ou au document d'exploitation.

## OWASP Top 10 (web/API) — recensement

| # | Risque | Statut FASO LOVE |
|---|---|---|
| A01 | Broken Access Control | ✅ Toute donnée personnelle filtrée par `get_current_user` + tests propriétaire-only (notifications 404 cross-user, paiements `/payments/{id}`, photos, profils) |
| A02 | Cryptographic Failures | ✅ TLS obligatoire en prod (+HSTS), JWT courtes + rotation/révocation instantanée, OTP à usage unique + haché côté stockage, EXIF des photos retirées |
| A03 | Injection | ✅ SQLAlchemy ORM paramétré partout ; un test dédié aux payloads d'injection (`test_security.py`) ; validation Pydantic stricte sur toutes les entrées |
| A04 | Insecure Design | ✅ Anti-spam OTP (cooldown, max tentatives, rate-limit), quotas freemium SERVEUR, machinerie de paiement idempotente (événement + requête), anti-spam notifications par conversation |
| A05 | Security Misconfiguration | ✅ En prod : /docs+OpenAPI désactivés, alertes de démarrage si configs DEV (JWT par défaut, CORS *, SMS console, simulation paiement), CORS par liste d'origines, headers HSTS/Permissions-Policy/nosniff/frame-deny/no-store |
| A06 | Vulnerable Components | ✅ `requirements.txt` **épinglé après audit pip-audit 26 sept. 2026 = 0 CVE déployée** (pillow 12.3, pyjwt 2.15, multipart 0.0.32, fastapi 0.141) ; renouvellement conseillé à chaque release |
| A07 | Identification & Auth Failures | ✅ OTP 6 chiffre 5 min, tentatives max 5, cooldown envoi, brute-force verify → 429, mines/âge vérifié SERVEUR, sessions révoquées à suppression de compte |
| A08 | Software & Data Integrity | ✅ Webhooks payants signés (HMAC PayDunya) + replay refusé + dédup événement GLOBALE (bug réel capturé en Phase 7 et corrigé) ; manifests sha256 des sauvegardes ; pins requirements.txt |
| A09 | Logging & Monitoring | ✅ Logs structurés serveur (actions critiques, push, modération) ; pas de données sensibles loggées ; monitoring externe reste à brancher (Phase 10 Sentry/Uptime-kuma recommandé) |
| A10 | SSRF | ✅ Aucune requête sortante pilotée par l'utilisateur (webhook passifs ; les URLs de callback viennent de la config ops, pas de l'input) |

## Dénis de service / masse

- ✅ Rate-limiting slowapi sur toutes les routes sensibles (OTP 120/min, chat, checkout 20/min, webhooks 240/min) — retours 429 cohérents.
- ✅ Uploads photos : lecture **plafonnée** (max+1 octets seulement en RAM), 413 propre au-delà de 10 Mo, recompression ≤1600 px, MIME vérifié.
- ✅ Messages chat : longueur bornée, match valide revalidé à chaud WS.
- ⬜ À faire Phase 10 : WAF/CDN devant l'API (Cloudflare gratuit suffit pour le pilote), limites UFW/iptables hôtes.

## Données & RGPD burkinabè

- ✅ Export intégral utilisateur (compte, profil, photos, messages, matchs, abonnements, transactions, notifications).
- ✅ Suppression de compte : effacement total, transactions comptables exclues (10 ans).
- ✅ Sauvegardes : gzip + sha256 + rotation 14, **chaîne dump→restore certifiée E2E** (témoin créé/supprimé/restauré avec profil intact).
- ⬜ Sous-traitance : chiffrer les sauvegardes à clé externe (age/gpg) en Phase 10, hébergement hors-sandbox.

## Processus

- ⬜ Suivi audit : pip-audit + licence-audit à chaque modification de `requirements.txt` (intégrable en CI Phase 10).
- ⬜ Validation juriste burkinabè des CGU/politique v1.0 (avant implémentation à grande échelle commerciale).
