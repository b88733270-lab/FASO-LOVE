"""Tests matching : orientation réciproque, réactions, matchs, exclusions."""

from tests.conftest import make_match


async def test_discover_orientation_reciproque(make_user, client):
    # Awa (F) cherche des hommes ; Idrissa (H) everyone ; Moussa (H) cherche femmes ;
    # Yacouba (H) cherche hommes → exclu de la file d'Awa (réciprocité).
    id_awa, _, h_awa = await make_user(
        display_name="Awa", gender="female", looking_for="male"
    )
    id_idrissa, _, _ = await make_user(
        display_name="Idrissa", gender="male", looking_for="everyone"
    )
    id_moussa, _, _ = await make_user(
        display_name="Moussa", gender="male", looking_for="female"
    )
    id_yacouba, _, _ = await make_user(
        display_name="Yacouba", gender="male", looking_for="male"
    )

    r = await client.get("/api/v1/discover", headers=h_awa)
    assert r.status_code == 200, r.text
    ids = [c["user_id"] for c in r.json()]
    assert id_idrissa in ids
    assert id_moussa in ids
    assert id_yacouba not in ids
    assert id_awa not in ids  # jamais soi-même


async def test_like_puis_match_reciproque_idempotent(make_user, client):
    id_a, _, h_a = await make_user(display_name="Fatimata", gender="female")
    id_b, _, h_b = await make_user(display_name="Souleymane", gender="male")

    # A like B → pas encore de match.
    r = await client.post(
        "/api/v1/discover/react",
        json={"target_user_id": id_b, "action": "like"},
        headers=h_a,
    )
    assert r.json()["matched"] is False

    # B like A → MATCH.
    r = await client.post(
        "/api/v1/discover/react",
        json={"target_user_id": id_a, "action": "like"},
        headers=h_b,
    )
    assert r.json()["matched"] is True
    match_id = r.json()["match_id"]
    assert match_id

    # Idempotence : B re-like A → même match, pas de doublon.
    r = await client.post(
        "/api/v1/discover/react",
        json={"target_user_id": id_a, "action": "super_like"},
        headers=h_b,
    )
    assert r.json()["matched"] is True
    assert r.json()["match_id"] == match_id

    # Le match apparaît dans la liste des deux côtés.
    for headers in (h_a, h_b):
        r = await client.get("/api/v1/matches", headers=headers)
        assert any(m["match_id"] == match_id for m in r.json())


async def test_profil_evalue_exclu_de_la_file(make_user, client):
    id_a, _, h_a = await make_user(display_name="Rasmata", gender="female")
    id_b, _, _ = await make_user(display_name="Aboubacar", gender="male")

    r = await client.get("/api/v1/discover", headers=h_a)
    assert id_b in [c["user_id"] for c in r.json()]

    await client.post(
        "/api/v1/discover/react",
        json={"target_user_id": id_b, "action": "pass"},
        headers=h_a,
    )
    r = await client.get("/api/v1/discover", headers=h_a)
    assert id_b not in [c["user_id"] for c in r.json()]


async def test_filtre_age(make_user, client):
    _, _, h_jeune = await make_user(display_name="JeuneF", gender="female", age=21)
    id_senior, _, _ = await make_user(display_name="SeniorH", gender="male", age=55)

    r = await client.get(
        "/api/v1/discover?min_age=18&max_age=30", headers=h_jeune
    )
    ids = [c["user_id"] for c in r.json()]
    assert id_senior not in ids

    r = await client.get(
        "/api/v1/discover?min_age=40&max_age=99", headers=h_jeune
    )
    ids = [c["user_id"] for c in r.json()]
    assert id_senior in ids


async def test_distance_triee(make_user, client):
    _, _, h_centre = await make_user(
        display_name="Ouaga", gender="female", latitude=12.3714, longitude=-1.5197
    )
    id_proche, _, _ = await make_user(
        display_name="Proche", gender="male", latitude=12.38, longitude=-1.52
    )
    id_lointain, _, _ = await make_user(
        display_name="Lointain", gender="male", city="Bobo-Dioulasso",
        latitude=11.1771, longitude=-4.2979,
    )

    r = await client.get("/api/v1/discover", headers=h_centre)
    cards = {c["user_id"]: c for c in r.json()}
    assert cards[id_proche]["distance_km"] < 5
    assert cards[id_lointain]["distance_km"] > 300
    # Tri croissant : le proche avant le lointain.
    order = [c["user_id"] for c in r.json()]
    assert order.index(id_proche) < order.index(id_lointain)

    # Filtre de distance : 50 km exclut Bobo.
    r = await client.get("/api/v1/discover?max_distance_km=50", headers=h_centre)
    ids = [c["user_id"] for c in r.json()]
    assert id_lointain not in ids and id_proche in ids


async def test_blocage_coupe_la_decouverte(make_user, client):
    id_a, _, h_a = await make_user(display_name="Vilaine", gender="female")
    id_b, _, h_b = await make_user(display_name="Cible", gender="male")

    # B bloque A → A ne voit plus B, et ne peut plus réagir.
    await client.post("/api/v1/blocks", json={"user_id": id_a}, headers=h_b)
    r = await client.get("/api/v1/discover", headers=h_a)
    assert id_b not in [c["user_id"] for c in r.json()]

    r = await client.post(
        "/api/v1/discover/react",
        json={"target_user_id": id_b, "action": "like"},
        headers=h_a,
    )
    assert r.status_code == 403


async def test_matches_dernier_message_et_non_lus(make_user, client):
    id_a, _, h_a = await make_user(display_name="Aminata", gender="female")
    id_b, _, h_b = await make_user(display_name="Boureima", gender="male")
    match_id = await make_match(client, h_a, h_b, id_a, id_b)

    # B envoie deux messages.
    for content in ("Salut Aminata !", "Comment tu vas ?"):
        r = await client.post(
            f"/api/v1/matches/{match_id}/messages",
            json={"content": content},
            headers=h_b,
        )
        assert r.status_code == 201

    # A voit 2 non-lus + le dernier message.
    matches = (await client.get("/api/v1/matches", headers=h_a)).json()
    m = next(m for m in matches if m["match_id"] == match_id)
    assert m["unread_count"] == 2
    assert m["last_message"]["content"] == "Comment tu vas ?"
    assert m["peer"]["display_name"] == "Boureima"

    # A marque comme lu → compteur retombe.
    r = await client.post(f"/api/v1/matches/{match_id}/read", headers=h_a)
    assert r.json()["read"] == 2
    matches = (await client.get("/api/v1/matches", headers=h_a)).json()
    m = next(m for m in matches if m["match_id"] == match_id)
    assert m["unread_count"] == 0
