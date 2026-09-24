"""Pipeline de traitement des photos de profil (Upload → disque local).

Sécurité & confidentialité :
- validation réelle du contenu via Pillow (pas de confiance à l'extension),
- **métadonnées EXIF supprimées** (géolocalisation embarquée, appareil…),
- re-encodage JPEG (neutralise les payloads non-image),
- redimensionnement ≤ 1600 px (poids maîtrisé pour les connexions limitées),
- quota de photos par utilisateur.

Phase 2b : basculer le stockage vers un objet S3/MinIO (même interface).
"""

import io
import uuid
from pathlib import Path

from PIL import Image

from app.core.config import get_settings

MAX_DIMENSION = 1600
JPEG_QUALITY = 85
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class MediaError(ValueError):
    """Fichier image invalide ou trop volumineux."""


def _media_root() -> Path:
    root = Path(get_settings().media_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_profile_photo(user_id: str, data: bytes) -> str:
    """Valide, nettoie et enregistre une photo. Retourne le chemin relatif."""
    settings = get_settings()
    max_bytes = settings.media_max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise MediaError(
            f"Image trop volumineuse (max {settings.media_max_upload_mb} Mo)."
        )
    if not data:
        raise MediaError("Fichier vide.")

    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise MediaError("Le fichier n'est pas une image valide.") from exc
    if img.format not in ALLOWED_FORMATS:
        raise MediaError("Format non pris en charge (JPEG, PNG ou WebP).")

    # Re-encodage propre : RGB sans EXIF, taille bornée.
    img = img.convert("RGB")
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    rel_path = f"{user_id}/{uuid.uuid4()}.jpg"
    target = _media_root() / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    # convert("RGB") produit une image SANS métadonnées : exif/jpeginfo ne
    # sont jamais recopiés → EXIF (GPS, appareil…) supprimé par construction.
    img.save(target, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return rel_path


def delete_profile_photo(file_path: str) -> None:
    """Supprime le fichier physique (best-effort)."""
    try:
        target = (_media_root() / file_path)
        root = _media_root()
        # Anti-traversée de chemin : le fichier doit rester sous media/.
        if root in target.resolve().parents or target.resolve().parent == root:
            target.unlink(missing_ok=True)
    except OSError:
        pass
