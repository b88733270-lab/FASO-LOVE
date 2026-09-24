#!/usr/bin/env python3
"""Jeu de données de DÉMONSTRATION FASO LOVE (profils burkinabè fictifs).

- 8 utilisateurs avec profils complets + photos (avatars génériques locaux,
  aucune personne réelle) répartis entre Ouagadougou et Bobo-Dioulasso ;
- 1 match prêt à l'emploi (Kadiatou ↔ Idrissa) avec historique ;
- 1 compte admin : +22670000099 (rôle admin — connexion par OTP console).

Idempotent : n'écrase rien si les numéros existent déjà.
Usage : SEED via tools_run_dev_api.py (automatique, SEED_DEMO=1) ou
        python3 tools_seed_demo.py
"""

import asyncio
import os
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PGDATA = BASE_DIR / ".pgdata"

if PGDATA.exists():
    os.environ.setdefault(
        "DATABASE_URL", f"postgresql+asyncpg://postgres@/fasolove?host={PGDATA}"
    )
os.environ.setdefault("JWT_SECRET", "dev-preview-secret-0123456789abcdef")

from app.core.security import utcnow  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.interactions import Like, Match, canonical_pair  # noqa: E402
from app.models.message import Message  # noqa: E402
from app.models.profile import Profile  # noqa: E402
from app.models.profile_photo import ProfilePhoto  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.media import save_profile_photo  # noqa: E402

PLACEHOLDERS = BASE_DIR.parent / "assets" / "placeholders"

DEMO_USERS = [
    # (téléphone, prénom, âge, genre, recherche, ville, lat, lng, bio, intérêts, avatar)
    ("+22670000001", "Kadiatou", 26, "female", "male", "Ouagadougou", 12.383, -1.545,
     "Couturière passionnée | Faso Dan Fani | J'aime les soirées maquis",
     ["Mode", "Cuisine", "Voyage"], 1),
    ("+22670000002", "Mariam", 24, "female", "everyone", "Ouagadougou", 12.355, -1.510,
     "Étudiante en médecine | Lectrice | Danse traditionnelle",
     ["Lecture", "Danse", "Musique"], 3),
    ("+22670000003", "Awa", 27, "female", "male", "Ouagadougou", 12.390, -1.520,
     "Coach sportive | Bien-être | Amoureuse de la nature",
     ["Sport", "Nature", "Photo"], 5),
    ("+22670000004", "Rasmata", 30, "female", "male", "Bobo-Dioulasso", 11.180, -4.300,
     "Entrepreneuse | Fan de théâtre | Voyageuse",
     ["Théâtre", "Voyage", "Artisanat"], 2),
    ("+22670000005", "Idrissa", 29, "male", "female", "Ouagadougou", 12.371, -1.530,
     "Informaticien | Mélomane | Footballeur du dimanche",
     ["Tech", "Football", "Musique"], 4),
    ("+22670000006", "Souleymane", 31, "male", "female", "Ouagadougou", 12.360, -1.480,
     "Chef cuisinier | Amateur de cinéma | Moto",
     ["Cuisine", "Cinéma", "Moto"], 6),
    ("+22670000007", "Moussa", 28, "male", "everyone", "Bobo-Dioulasso", 11.170, -4.290,
     "Enseignant | Poète à mes heures | Jardinage",
     ["Écriture", "Langues", "Jardinage"], 2),
    ("+22670000008", "Abdoulaye", 34, "male", "female", "Ouagadougou", 12.350, -1.560,
     "Chauffeur-entrepreneur | Humour | Bénévolat",
     ["Bénévolat", "Sport", "Jeux"], 1),
]

ADMIN_PHONE = "+22670000099"


def _birth(age: int) -> date:
    today = utcnow().date()
    return date(today.year - age, 6, 15)


async def seed() -> int:
    created = 0
    async with AsyncSessionLocal() as db:
        ids: dict[str, str] = {}
        for phone, name, age, gender, looking, city, lat, lng, bio, interests, avatar in DEMO_USERS:
            from sqlalchemy import select

            existing = await db.scalar(select(User).where(User.phone_e164 == phone))
            if existing is not None:
                ids[phone] = existing.id
                continue
            user = User(
                phone_e164=phone, birthdate=_birth(age), is_verified=True
            )
            db.add(user)
            await db.flush()
            db.add(
                Profile(
                    user_id=user.id,
                    display_name=name,
                    gender=gender,
                    looking_for=looking,
                    bio=bio,
                    city=city,
                    interests=interests,
                    latitude=lat,
                    longitude=lng,
                )
            )
            avatar_file = PLACEHOLDERS / f"avatar_{avatar}.png"
            rel = save_profile_photo(user.id, avatar_file.read_bytes())
            db.add(
                ProfilePhoto(user_id=user.id, file_path=rel, status="approved")
            )
            ids[phone] = user.id
            created += 1

        # Admin de démonstration.
        from sqlalchemy import select

        admin = await db.scalar(select(User).where(User.phone_e164 == ADMIN_PHONE))
        if admin is None:
            admin = User(
                phone_e164=ADMIN_PHONE,
                birthdate=_birth(35),
                role="admin",
                is_verified=True,
            )
            db.add(admin)
            await db.flush()
            db.add(
                Profile(
                    user_id=admin.id,
                    display_name="Équipe FASO LOVE",
                    gender="female",
                    looking_for="everyone",
                    bio="Compte de modération.",
                    city="Ouagadougou",
                    interests=[],
                )
            )
            created += 1

        # Match de démonstration Kadiatou ↔ Idrissa (+ historique).
        kadia = ids.get("+22670000001")
        idrissa = ids.get("+22670000005")
        if kadia and idrissa:
            low, high = canonical_pair(kadia, idrissa)
            match = await db.scalar(
                select(Match).where(Match.user_low == low, Match.user_high == high)
            )
            if match is None:
                db.add(Like(from_user_id=kadia, to_user_id=idrissa, action="like"))
                db.add(Like(from_user_id=idrissa, to_user_id=kadia, action="like"))
                match = Match(user_low=low, user_high=high)
                db.add(match)
                await db.flush()
                db.add_all(
                    [
                        Message(match_id=match.id, sender_id=idrissa,
                                content="Bonjour Kadiatou ! Ravie de notre match 😊"),
                        Message(match_id=match.id, sender_id=kadia,
                                content="Bonjour Idrissa ! Moi de même 🤝"),
                        Message(match_id=match.id, sender_id=idrissa,
                                content="On se retrouve au maquis le week-end prochain ?"),
                    ]
                )
                created += 1

        await db.commit()
    return created


async def main() -> None:
    created = await seed()
    print(f"🌱 Seed démo : {created} nouvelles entités créées.")
    print("   Comptes test (OTP en console) : +22670000001 … +22670000008")
    print("   Compte admin                  : +22670000099")


if __name__ == "__main__":
    asyncio.run(main())
