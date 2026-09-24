#!/bin/sh
# FASO LOVE — sauvegarde Postgres dans le conteneur `backup` (Phase 10).
#
# Exécution (cron hôte, quotidien 03:25 UTC) :
#   25 3 * * * docker compose -f infra/docker-compose.prod.yml --env-file infra/.env run --rm backup /docker-backup.sh
#
# Le manifeste sha256 est rafraîchi ; rotation : $BACKUP_KEEP archives max.

set -eu

DEST=/backups/fasolove-$(date -u +%Y%m%d-%H%M%S).sql.gz
KEEP="${BACKUP_KEEP:-30}"

echo "[backup] dump → $DEST"
pg_dump --no-owner --clean --if-exists | gzip > "$DEST.tmp"
SHA=$(sha256sum "$DEST.tmp" | awk '{print $1}')
mv "$DEST.tmp" "$DEST"
echo "$SHA  $(basename "$DEST")" >> /backups/manifest.sha256

# Rotation : ne garder que les $KEEP plus récentes.
ls -1t /backups/fasolove-*.sql.gz 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r vieux; do
    rm -f "$vieux"
    echo "[backup] rotation : $(basename "$vieux") supprimé"
done

echo "[backup] ✅ $(basename "$DEST") ($(du -h "$DEST" | cut -f1), sha256 ${SHA:0:16}…)"
