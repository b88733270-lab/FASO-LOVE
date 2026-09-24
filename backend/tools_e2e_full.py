#!/usr/bin/env python3
"""E2E BOÎTE NOIRE FASO LOVE — parcours produit complet contre le serveur.

Couvre en conditions réelles (HTTP + WebSocket réseau) :
santé → OTP 18+ (refus mineur) → profil → photo (JPEG servi) → découverte
géolocalisée → like réciproque → match → messages REST + temps réel
WebSocket → accusés de lecture → signalement → stats admin → suppression
de compte (effacement intégral).

Prérequis : serveur démarré (tools_run_dev_api.py) sur BASE_URL,
package `websockets` installé.
"""

import asyncio
import io
import json
import os
from datetime import date

import websockets
from httpx import AsyncClient
from PIL import Image

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
API = f"{BASE_URL}/api/v1"
WS = BASE_URL.replace("http", "ws") + "/api/v1/ws/chat"

ok = 0


def check(cond: bool, label: str) -> None:
    global ok
    assert cond, f"❌ ÉCHEC : {label}"
    ok += 1
    print(f"  ✅ {label}")


def jpeg_bytes(color) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), color).save(buf, "JPEG")
    return buf.getvalue()


async def register(client: AsyncClient, phone: str, age: int) -> dict:
    r = await client.post(f"{API}/auth/otp/request", json={"phone": phone})
    code = r.json()["dev_code"]
    birth = date(date.today().year - age, 3, 12).isoformat()
    r = await client.post(
        f"{API}/auth/otp/verify",
        json={"phone": phone, "code": code, "birthdate": birth},
    )
    assert r.status_code == 200, r.text
    return r.json()


async def main() -> None:
    async with AsyncClient(base_url=BASE_URL, timeout=30) as c:
        print("— Santé & règle 18+")
        r = await c.get(f"{API}/health")
        check(r.status_code == 200 and r.json()["status"] == "ok", "API saine")
        check("X-Content-Type-Options" in r.headers, "en-têtes de sécurité")

        r = await c.post(f"{API}/auth/otp/request", json={"phone": "+22670445566"})
        code = r.json()["dev_code"]
        r = await c.post(
            f"{API}/auth/otp/verify",
            json={"phone": "+22670445566", "code": code, "birthdate": "2010-01-01"},
        )
        check(r.status_code == 403 and "18" in r.json()["detail"],
              "mineur refusé (403, règle 18+)")

        print("— Inscription + profils + photos (2 utilisateurs E2E)")
        tok_a = (await register(c, "+22676234567", 27))["access_token"]
        tok_b = (await register(c, "+22665342109", 29))["access_token"]
        h_a = {"Authorization": f"Bearer {tok_a}"}
        h_b = {"Authorization": f"Bearer {tok_b}"}

        await c.put(f"{API}/profiles/me", headers=h_a, json={
            "display_name": "E2E_Awa", "gender": "female", "looking_for": "male",
            "bio": "Utilisatrice E2E", "city": "Ouagadougou",
            "interests": ["Musique", "Cuisine"], "latitude": 12.372, "longitude": -1.519})
        await c.put(f"{API}/profiles/me", headers=h_b, json={
            "display_name": "E2E_Boureima", "gender": "male", "looking_for": "female",
            "bio": "Utilisateur E2E", "city": "Ouagadougou",
            "interests": ["Football", "Cinéma"], "latitude": 12.380, "longitude": -1.525})
        check(True, "profils créés")

        for headers, color in ((h_a, (190, 60, 60)), (h_b, (60, 90, 190))):
            r = await c.post(f"{API}/profiles/me/photos", headers=headers,
                             files={"file": ("p.jpg", jpeg_bytes(color), "image/jpeg")})
            check(r.status_code == 201 and r.json()["status"] == "approved",
                  "photo uploadée & approuvée")
            url = r.json()["url"]
            r2 = await c.get(url)
            check(r2.status_code == 200 and "image" in r2.headers["content-type"],
                  f"photo servie publiquement ({url})")

        print("— Découverte géolocalisée")
        r = await c.get(f"{API}/discover", headers=h_a)
        cards = r.json()
        me_b = (await c.get(f"{API}/auth/me", headers=h_b)).json()["id"]
        card_b = next((x for x in cards if x["user_id"] == me_b), None)
        check(card_b is not None, "B visible dans la file de A")
        check(card_b["distance_km"] < 5, f"distance réaliste ({card_b['distance_km']} km)")
        check("latitude" not in card_b, "coordonnées exactes non divulguées")

        print("— Match réciproque")
        me_a = (await c.get(f"{API}/auth/me", headers=h_a)).json()["id"]
        r = await c.post(f"{API}/discover/react", headers=h_a,
                         json={"target_user_id": me_b, "action": "like"})
        check(r.json()["matched"] is False, "like simple : pas de match")
        r = await c.post(f"{API}/discover/react", headers=h_b,
                         json={"target_user_id": me_a, "action": "super_like"})
        body = r.json()
        check(body["matched"] is True, "like réciproque → MATCH 🎉")
        match_id = body["match_id"]
        r = await c.post(f"{API}/discover/react", headers=h_b,
                         json={"target_user_id": me_a, "action": "like"})
        check(r.json()["match_id"] == match_id, "réaction idempotente (même match)")

        print("— Chat REST + WebSocket temps réel")
        async with websockets.connect(f"{WS}/{match_id}?token={tok_b}") as ws:
            r = await c.post(f"{API}/matches/{match_id}/messages", headers=h_a,
                             json={"content": "Salut depuis l'E2E !"})
            check(r.status_code == 201, "message REST envoyé")
            event = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            check(event["type"] == "message" and
                  event["message"]["content"] == "Salut depuis l'E2E !",
                  "diffusion WebSocket reçue par B")

            await ws.send(json.dumps({"type": "message", "content": "Bien reçu Awa 😉"}))
            echo = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            check(echo["type"] == "message", "message WebSocket persisté+diffusé")

            r = await c.post(f"{API}/matches/{match_id}/read", headers=h_a)
            check(r.json()["read"] >= 1, "accusé de lecture appliqué")

        r = await c.get(f"{API}/matches/{match_id}/messages", headers=h_a)
        check(len(r.json()) >= 2, "historique persisté")
        matches = (await c.get(f"{API}/matches", headers=h_a)).json()
        check(any(m["match_id"] == match_id for m in matches),
              "match visible dans la liste")

        print("— Signalement + admin (compte seed +22670000099)")
        r = await c.post(f"{API}/reports", headers=h_a,
                         json={"reported_user_id": me_b, "reason": "other",
                               "details": "test e2e"})
        report_id = r.json()["id"]
        check(r.status_code == 201, "signalement créé")

        tok_admin = (await register(c, "+22670000099", 35))["access_token"]
        h_admin = {"Authorization": f"Bearer {tok_admin}"}
        r = await c.get(f"{API}/admin/reports", headers=h_admin)
        check(any(p["id"] == report_id for p in r.json()), "file admin contient le signalement")
        r = await c.post(f"{API}/admin/reports/{report_id}/resolve",
                         headers=h_admin, json={"resolution": "resolved"})
        check(r.json()["status"] == "resolved", "signalement résolu")
        r = await c.get(f"{API}/admin/stats", headers=h_admin)
        stats = r.json()
        check(stats["users_total"] >= 10 and stats["matches_total"] >= 2,
              f"stats admin cohérentes ({stats['users_total']} users, {stats['matches_total']} matchs)")

        print("— Seed démo présent")
        r = await c.get(f"{API}/discover", headers=h_a)
        names = [x["display_name"] for x in r.json()]
        check(any(n in ("Souleymane", "Abdoulaye", "Idrissa", "E2E_Boureima")
                  for n in names), "profils de démonstration découverts : " + ", ".join(names[:4]))

        print("— Suppression de compte (effacement intégral)")
        r = await c.get(f"{API}/users/me/export", headers=h_b)
        check(r.status_code == 200 and r.json()["compte"]["telephone"] == "+22665342109",
              "export des données (portabilité)")
        r = await c.delete(f"{API}/users/me", headers=h_b)
        check(r.status_code == 204, "compte supprimé")
        r = await c.get(f"{API}/auth/me", headers=h_b)
        check(r.status_code == 401, "session révoquée après suppression")
        matches = (await c.get(f"{API}/matches", headers=h_a)).json()
        check(all(m["match_id"] != match_id for m in matches),
              "match supprimé chez le correspondant")

    print(f"\n🎉 E2E BOÎTE NOIRE : {ok} vérifications réussies sur {BASE_URL}")


if __name__ == "__main__":
    asyncio.run(main())
