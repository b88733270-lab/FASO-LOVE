#!/usr/bin/env python3
"""Restauration d'une sauvegarde FASO LOVE (Phase 9).

⚠️  Toute restauration est DÉFINITIVE : les données actuelles de la base
    sont effacées (`pg_dump --clean --if-exists` rejoué). Passer `--force`
    pour confirmer sur un environnement connu ; penser à sauvegarder la
    base courante AVANT (`tools_backup_db.py`).

Usage : ./.venv/bin/python tools_restore_db.py backups/fasolove-20250925-101500.sql.gz --force
"""

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PGDATA = os.path.join(BASE_DIR, ".pgdata")


def _pgbin() -> str:
    import pgserver  # type: ignore

    root = os.path.dirname(pgserver.__file__)
    for dossier in (os.path.join(root, "pginstall", "bin"), os.path.join(root, "bin")):
        if os.path.exists(os.path.join(dossier, "psql")):
            return dossier
    return "psql"


def _env_pg() -> dict:
    env = dict(os.environ)
    env.setdefault("PGHOST", PGDATA)
    env.setdefault("PGUSER", "postgres")
    env.setdefault("PGDATABASE", "fasolove")
    return env


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fichier")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.force:
        print("❌ Restauration DÉFINITIVE — relancer avec --force.", file=sys.stderr)
        return 2
    if not os.path.exists(args.fichier):
        print(f"❌ Fichier introuvable : {args.fichier}", file=sys.stderr)
        return 1

    # Vérifier le checksum contre le manifeste quand il existe.
    manifeste_chemin = os.path.join(
        os.path.dirname(os.path.abspath(args.fichier)), "manifest.json"
    )
    if os.path.exists(manifeste_chemin):
        sha = hashlib.sha256()
        with open(args.fichier, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                sha.update(chunk)
        with open(manifeste_chemin) as fh:
            manifeste = {e["fichier"]: e for e in json.load(fh)}
        attendu = manifeste.get(os.path.basename(args.fichier), {}).get("sha256")
        if attendu and attendu != sha.hexdigest():
            print("❌ Checksum ne correspond pas au manifeste — archive suspecte.", file=sys.stderr)
            return 1
        print("[restore] checksum ✓")

    env = _env_pg()
    psql = os.path.join(_pgbin(), "psql")
    print(f"[restore] restauration de {args.fichier} (DÉFINITIVE)…")
    with gzip.open(args.fichier, "rb") as gz:
        sql = gz.read()  # GzipFile.fileno() délègue au fichier BRUT : ne
        # jamais le brancher directement sur le stdin d'un sous-processus.
    result = subprocess.run(
        [psql, "-q", "-v", "ON_ERROR_STOP=1"],
        env=env, input=sql, capture_output=True,
    )
    if result.returncode != 0:
        print(
            f"[restore] ❌ échec : {result.stderr.decode(errors='replace')[:400]}",
            file=sys.stderr,
        )
        return 1
    print("[restore] ✅ base restaurée. Redémarrer l'API pour laisser le pool prendre la nouvelle version.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
