# Audit de sécurité — Phase 9 (25 septembre 2026)

## 1. Audit des dépendances (pip-audit)

Exécuté ce jour contre l'environnement de production épingle
(`backend/requirements.txt`).

**Avant audit** (combinaison initiale 2025) :

- `pillow==11.3.0` : **19 vulnérabilités** (écritures hors limites natives,
  DoS par PDF/GED boucles infinies, lecture hors buffer font/PSD/TGA…) — fix
  12.1.1 → 12.3.0 selon CVE ;
- `python-multipart==0.0.20` : **6 vulnérabilités** (Path Traversal config non
  par défaut, DoS multipart, Content-Length non validée) — fix ≤ 0.0.31 ;
- `pyjwt==2.10.1` : **7 vulnérabilités** (validation `crit`, ECC vérif,
  JWKClient contournement) — fix ≤ 2.13.0 ;
- `fastapi==0.116.1`/`starlette==0.47.3` : **8 vulnérabilités starlette**
  (Host header Header reconstruction, Range header crafted, StaticFiles path
  Windows) — fix ≤ 1.3.1 (ce qui impose la montée FastAPI associée) ;
- `pip`/`setuptools` (outillage local, hors déploiement) : documentés, non
  scope produit (à mettre à jour par venv neuf).

**Action** : upgrade conjoint et épinglage :

```
fastapi==0.141.1 · starlette==1.7.0 · pillow==12.3.0 · pyjwt==2.15.0
python-multipart==0.0.32 (les autres inchangées)
```

→ **Après bump : 0 vulnérabilité déployée connue selon la base CVEdumps
(evaluation pip-audit)** — vérification à refaire à chaque release (CI Phase 10).

**Risque de compatibilité** : 79/79 tests pytest verts après la montée de
versions (pillow 12 — API de compression inchangée pour notre usage ;
FastAPI 0.141 — comportements Pydantic inchangés) + E2E boîte noire 45/45 ✔.

## 2. Revue du code serveur

| Perspective | Mesures effective(s) |
|---|---|
| Surface d'exposition | `/docs`, `/openapi.json` désactivés si `ENV=prod` ; pas de diagnostic interne dans les 4xx/5xx |
| Headers HTTP | `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, **HSTS** en prod, `Permissions-Policy` restrictive (géoloc/caméra/micro/paiement/USB tous `()`) |
| Cache sensible | `Cache-Control: no-store` sur auth/utilisateurs/abonnements |
| Uploads | lecture plafonnée max+1 en mémoire (plus de ram bomb) → 413 propre ; MIME + content → pillow recompression <= 1600 px, EXIF stripped |
| Entries | Pydantic strict ; enums/regex partout (`platform` ∈ android/ios/web…) |
| Authentification | OTP code 6 chiffres, usage unique + TTL 5 min ; OTP hashé en base ; max 5 tentatives ; cooldown entre envois ; 429 normalisé anti-énumération |
| Sessions | JWT courte (30 min) + refresh 30 jours à usage unique avec rotation ; révocation à suppression de compte testée |
| Vérification d'âge | **côté SERVEUR** à chaque nouvelle session (jamais purement client) ; testé pour les éventuels age tricks (bornes 17.999 → refusé) |
| Paiement | checkout idempotence requête 15 min + événement global (bug Phase 7 corrigé), webhook HMAC + replay interdit + toujours-200 (aucune fuite d'existence), rôle admin en base jamais côté client |
| Modération | file admin : rôle lu exclusivement côté serveur (colonne `role`, non editable via API) ; signalements horodatés |
| Configuration | **garde-fou au démarrage ENV=prod** : journalise une alerte pour chaque variable restée sur sa valeur DEV |

## 3. Continuité (sauvegarde/restauration)

- `tools_backup_db.py` : dump pg_dump gzip horodaté + `manifest.json` (sha256,
  effectifs métier) + rotation paramétrable ; audit gitignore (jamais
  versionné).
- `tools_restore_db.py` : vérification du checksum avant tout, `--force`
  explicite, bandeau de sauvegarde préventive.
- `tools_e2e_backup.py` : certification à la demande — témoin créé via API,
  sauvegardé, supprimé puis **restauré avec son profil intact** (uid
  conservé, prouvant l'intégrité des clés et de la sérialisation). Validé.

## 4. Limite résiduelle (assumée, documentée)

- Hébergement sandbox : Postgres immédiat `pgserver`, sauvegardes sur le
  même volume → en prod : disque/zone distincte + chiffrement off-site.
- Anti-fraude comportementale (romance scams) = modération réactive pour le
  pilote ; détection heuristique prévue Phase 10.
- Chiffrement à l'arrêt au niveau base : délégué au stockage hébergeur
  (disk encryption) sur le même principe des médias.

## 5. Cadre juridique finalisé

- `docs/CGU_FASO_LOVE.md` **v1.0** : 10 articles clés (éligibilité 18+,
  Premium/paiement Mobile Money, rétractation, anti-escroquerie romantique,
  modération 24-48 h, responsabilité, loi burkinabè + for Ouagadougou).
- `docs/POLITIQUE_CONFIDENTIALITE_FASO_LOVE.md` **v1.0** : collecte/finalités,
  sous-traitants (SMS, PayDunya, hébergeur), durées de conservation
  justifiées, droits in-app (conséquent avec la mise en œuvre), CIL.
- `docs/MENTIONS_LEGALES.md` nouveau (RCCM à compléter à l'immatriculation).
