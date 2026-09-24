"""Envoi de SMS — abstraction fournisseur.

- **Dev** : `ConsoleSmsSender` imprime le code dans les logs (comportement
  par défaut, `SMS_PROVIDER=console`, à combiner avec `OTP_DEV_ECHO=true`).
- **Phase 1b (production)** : implémenter ici l'adaptateur de l'agrégateur
  retenu pour le Burkina Faso (ex. Africa's Talking couvre le +226 ;
  Orange SMS API). La signature de [SmsSender] ne changera pas.
"""

import logging
from typing import Protocol

from app.core.config import get_settings

logger = logging.getLogger("fasolove.sms")


class SmsSender(Protocol):
    async def send_otp(self, phone_e164: str, code: str) -> None: ...


class ConsoleSmsSender:
    """Fournisseur de développement : log le code OTP au lieu d'envoyer un SMS."""

    async def send_otp(self, phone_e164: str, code: str) -> None:
        logger.warning(
            "📲 SMS (console, DEV SEULEMENT) → %s : code FASO LOVE %s",
            phone_e164,
            code,
        )


def get_sms_sender() -> SmsSender:
    """Fabrique du fournisseur SMS selon la configuration."""
    settings = get_settings()
    match settings.sms_provider:
        case "console":
            return ConsoleSmsSender()
        case other:
            # Phase 1b : "africas_talking" | "orange_sms" → adaptateurs HTTP.
            raise RuntimeError(
                f"Fournisseur SMS inconnu : {other!r} "
                "(seuls 'console' est implémenté pour l'instant)"
            )
