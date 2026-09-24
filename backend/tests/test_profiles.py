"""Tests profils : création, visibilité publique/privée, photos modérées."""

from datetime import date

from app.core.config import get_settings

from tests.conftest import tiny_jpeg


async def test_upsert_et_lecture_mon_profil(make_user, client):
    user_id, _, headers = await make_user(display_name="Awa", age=30)

    r = await client.get("/api/v1/profiles/me", headers=headers)
    assert r.status_code == 200
    me = r.json()
    assert me["display_name"] == "Awa"
    assert me["age"] == date.today().year - (date.today().year - 30)
    assert me["latitude"] is not None and me["longitude"] is not None
    assert len(me["photos"]) == 1
    assert me["photos"][0]["status"] == "approved"
    assert me["photos"][0]["url"].startswith("/media/")


async def test_profil_public_ne_divulgue_pas_les_coordonnees(make_user, client):
    _, _, headers_b = await make_user(display_name="Idrissa", gender="male", age=29)
    user_id_a, _, _ = await make_user(display_name="Mariam", age=25)

    r = await client.get(f"/api/v1/profiles/{user_id_a}", headers=headers_b)
    assert r.status_code == 200
    pub = r.json()
    assert "latitude" not in pub and "longitude" not in pub
    assert pub["display_name"] == "Mariam"


async def test_catalogue_interets(client):
    r = await client.get("/api/v1/profiles/catalog/interests")
    assert r.status_code == 200
    assert "Musique" in r.json()["interests"]


async def test_upload_invalide(make_user, client):
    _, _, headers = await make_user(with_photo=False)

    # Fichier qui n'est pas une image → 422 explicite.
    r = await client.post(
        "/api/v1/profiles/me/photos",
        files={"file": ("fichier.jpg", b"pas une image", "image/jpeg")},
        headers=headers,
    )
    assert r.status_code == 422


async def test_photo_servie_via_media(make_user, client):
    _, _, headers = await make_user()
    r = await client.get("/api/v1/profiles/me", headers=headers)
    url = r.json()["photos"][0]["url"]
    r = await client.get(url)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/")


async def test_suppression_photo(make_user, client):
    _, _, headers = await make_user()
    photo_id = (await client.get("/api/v1/profiles/me", headers=headers)).json()[
        "photos"
    ][0]["id"]

    r = await client.delete(f"/api/v1/profiles/me/photos/{photo_id}", headers=headers)
    assert r.status_code == 204
    photos = (await client.get("/api/v1/profiles/me", headers=headers)).json()[
        "photos"
    ]
    assert photos == []


async def test_quota_photos(make_user, client):
    settings = get_settings()
    original = settings.media_max_photos_per_user
    settings.media_max_photos_per_user = 1
    try:
        _, _, headers = await make_user(with_photo=True)  # 1ère photo OK
        r = await client.post(
            "/api/v1/profiles/me/photos",
            files={"file": ("p2.jpg", tiny_jpeg((30, 120, 60)), "image/jpeg")},
            headers=headers,
        )
        assert r.status_code == 409  # quota atteint
    finally:
        settings.media_max_photos_per_user = original


async def test_genre_invalide(make_user, client):
    _, _, headers = await make_user(with_photo=False)
    r = await client.put(
        "/api/v1/profiles/me",
        json={"display_name": "Test", "gender": "invalide"},
        headers=headers,
    )
    assert r.status_code == 422
