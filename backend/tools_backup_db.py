#!/usr/bin/env python3
"""Sauvegarde de la base FASO LOVE (Phase 9 — sécurité & continuité).

- `pg_dump` compressé (gzip) horodaté dans `backups/` (GIT-IGNORÉ — jamais
  de données client dans le dépôt) ;
- manifeste `manifest.json` enrichi à chaque passage : fichier, sha256,
  taille et effectifs métier (utilisateurs/conversations/notifications…) —
  c'est ce qui permet de VALIDER la sauvegarde avant de la restaurer ;
- rotation automatique : on ne garde que les N (par défaut 14) dernières.

Cron recommandé (production) — voir docs/RUNBOOK_OPERATIONS.md :

    25 3 * * * cd /opt/fasolove/backend && ./.venv/bin/python tools_backup_db.py --keep 30 >> /var/log/fasolove-backup.log 2>&1

Usage : ./.venv/bin/python tools_backup_db.py [--dir backups] [--keep 14]
"""

import argparse
import gzip
import hashlib
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PGDATA = os.path.join(BASE_DIR, ".pgdata")


def _pgbin() -> str:
    """Chemin des binaires PostgreSQL livrés par pgserver (pg_dump/psql)."""
    import pgserver  # type: ignore

    root = os.path.dirname(pgserver.__file__)
    candidats = [
        os.path.join(root, "pginstall", "bin"),
        os.path.join(root, "bin"),
    ]
    for dossier in candidats:
        if os.path.exists(os.path.join(dossier, "pg_dump")):
            return dossier
    return "pg_dump"  # binaire système (path)


def _env_pg() -> dict:
    env = dict(os.environ)
    # connexion par socket Unix (bau du runner dev) ; hors-sandbox, mettez
    # PGHOST/PGPORT/PGUSER/PGPASSWORD depuis le vault.
    env.setdefault("PGHOST", PGDATA)
    env.setdefault("PGUSER", "postgres")
    env.setdefault("PGDATABASE", "fasolove")
    return env


def _compteurs(env: dict, pgbin: str) -> dict:
    """Effectifs tsensor du manifeste (preuve que le dump n'est pas vide)."""
    sql = (
        "SELECT (SELECT count(*) FROM users) || ',' || "
        "(SELECT count(*) FROM matches) || ',' || "
        "(SELECT count(*) FROM messages) || ',' || "
        "(SELECT count(*) FROM payment_transactions)"
    )
    try:
        out = subprocess.run(
            [os.path.join(pgbin, "psql"), "-Atqc", sql],
            env=env, capture_output=True, text=True, timeout=30,
        )
        if out.returncode == 0 and out.stdout.strip():
            u, m, msg, t = out.stdout.strip().split(",")
            return {
                "users": int(u), "matches": int(m),
                "messages": int(msg), "payment_transactions": int(t),
            }
    except Exception:
        pass
    return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default=os.path.join(BASE_DIR, "backups"))
    parser.add_argument("--keep", type=int, default=14)
    args = parser.parse_args()

    os.makedirs(args.dir, exist_ok=True)
    pgbin = _pgbin()
    env = _env_pg()

    horodatage = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    fichier = os.path.join(args.dir, f"fasolove-{horodatage}.sql.gz")
    dump_cmd = shlex.split(
        f"{os.path.join(pgbin, 'pg_dump')} --no-owner --clean --if-exists"
    )

    print(f"[backup] dump → {fichier}")
    with subprocess.Popen(
        dump_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) as pg, gzip.open(fichier, "wb") as gz:
        assert pg.stdout is not None
        for chunk in iter(lambda: pg.stdout.read(1 << 16), b""):
            gz.write(chunk)
        _, err = pg.communicate()
    if pg.returncode != 0:
        os.unlink(fichier)
        print(f"[backup] ❌ échec pg_dump : {err.decode()[:400]}", file=sys.stderr)
        return 1

    sha = hashlib.sha256()
    taille = 0
    with open(fichier, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            sha.update(chunk)
            taille += len(chunk)

    manifeste_chemin = os.path.join(args.dir, "manifest.json")
    manifeste = []
    if os.path.exists(manifeste_chemin):
        with open(manifeste_chemin) as fh:
            manifeste = json.load(fh)
    manifeste.append(
        {
            "fichier": os.path.basename(fichier),
            "cree_le": datetime.now(timezone.utc).isoformat(),
            "taille_octets": taille,
            "sha256": sha.hexdigest(),
            "compteurs": _compteurs(env, pgbin),
        }
    )
    # Rotation : supprimer les plus anciens au-delà de --keep.
    manifeste.sort(key=lambda e: e["cree_le"])
    while len(manifeste) > args.keep:
        retire = manifeste.pop(0)
        vieux = os.path.join(args.dir, retire["fichier"])
        if os.path.exists(vieux):
            os.unlink(vieux)
        print(f"[backup] rotation : {retire['fichier']} supprimé")
    with open(manifeste_chemin, "w") as fh:
        json.dump(manifeste, fh, indent=2, ensure_ascii=False)

    print(
        f"[backup] ✅ {taille / 1024:.0f} Ko compressés, sha256 {sha.hexdigest()[:16]}… "
        f"({len(manifeste)} sauvegarde(s) conservées)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
