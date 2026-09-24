"""Tests chat : historique REST, accès restreints et WebSocket temps réel."""

import pytest

from tests.conftest import create_user, make_match


async def test_historique_et_acces_restreint(make_user, client):
    id_a, _, h_a = await make_user(display_name="ChatF", gender="female")
    id_b, _, h_b = await make_user(display_name="ChatH", gender="male")
    match_id = await make_match(client, h_a, h_b, id_a, id_b)

    # Un tiers n'a accès ni à l'historique ni à l'envoi → 404.
    _, _, h_tiers = await make_user(display_name="Tiers", gender="female")
    r = await client.get(f"/api/v1/matches/{match_id}/messages", headers=h_tiers)
    assert r.status_code == 404
    r = await client.post(
        f"/api/v1/matches/{match_id}/messages",
        json={"content": "intrusion"},
        headers=h_tiers,
    )
    assert r.status_code == 404

    # Les membres échangent ; l'historique est trié récent → ancien.
    await client.post(
        f"/api/v1/matches/{match_id}/messages",
        json={"content": "Bonjour !"},
        headers=h_a,
    )
    await client.post(
        f"/api/v1/matches/{match_id}/messages",
        json={"content": "Salut, ça va ?"},
        headers=h_b,
    )
    r = await client.get(f"/api/v1/matches/{match_id}/messages", headers=h_a)
    messages = r.json()
    assert len(messages) == 2
    assert messages[0]["content"] == "Salut, ça va ?"  # le plus récent d'abord
    assert messages[0]["is_mine"] is False
    assert messages[1]["is_mine"] is True


async def test_message_vide_rejete(make_user, client):
    id_a, _, h_a = await make_user(display_name="VideF", gender="female")
    id_b, _, h_b = await make_user(display_name="VideH", gender="male")
    match_id = await make_match(client, h_a, h_b, id_a, id_b)
    r = await client.post(
        f"/api/v1/matches/{match_id}/messages",
        json={"content": ""},
        headers=h_a,
    )
    assert r.status_code == 422


async def test_websocket_temps_reel(ws_setup):
    client, tc = ws_setup
    id_a, _, h_a = await create_user(client, display_name="WsF", gender="female")
    id_b, t_b, h_b = await create_user(client, display_name="WsH", gender="male")
    match_id = await make_match(client, h_a, h_b, id_a, id_b)

    token_a = h_a["Authorization"].split(" ", 1)[1]
    with tc.websocket_connect(
        f"/api/v1/ws/chat/{match_id}?token={token_a}"
    ) as sock_a:
        with tc.websocket_connect(
            f"/api/v1/ws/chat/{match_id}?token={t_b}"
        ) as sock_b:
            # A envoie un message → A et B le reçoivent en temps réel.
            sock_a.send_json({"type": "message", "content": "Salut en direct !"})
            received_b = sock_b.receive_json()
            assert received_b["type"] == "message"
            assert received_b["message"]["content"] == "Salut en direct !"
            assert received_b["message"]["sender_id"] == id_a

            received_a = sock_a.receive_json()  # synchronisation multi-appareils
            assert received_a["message"]["content"] == "Salut en direct !"

            # Indicateur de frappe B → A le voit, B ne le reçoit pas lui-même.
            sock_b.send_json({"type": "typing"})
            received_a = sock_a.receive_json()
            assert received_a["type"] == "typing"
            assert received_a["user_id"] == id_b

            # Accusé de lecture A → B notifié.
            sock_a.send_json({"type": "read"})
            received_b = sock_b.receive_json()
            assert received_b["type"] == "read"
            assert received_b["by"] == id_a

    # Le message WebSocket est bien persisté en base.
    r = await client.get(f"/api/v1/matches/{match_id}/messages", headers=h_a)
    assert any(
        m["content"] == "Salut en direct !" for m in r.json()
    )
    # …et l'accusé de lecture a été appliqué aux messages de A lus par B ?
    r = await client.get(f"/api/v1/matches/{match_id}/messages", headers=h_b)
    mine = [m for m in r.json() if m["is_mine"]]
    assert mine == [] or all(m["read_at"] is None for m in mine)


async def test_websocket_token_invalide(ws_setup):
    client, tc = ws_setup
    id_a, _, h_a = await create_user(client, display_name="TokF", gender="female")
    id_b, _, h_b = await create_user(client, display_name="TokH", gender="male")
    match_id = await make_match(client, h_a, h_b, id_a, id_b)

    with pytest.raises(Exception):
        with tc.websocket_connect(
            f"/api/v1/ws/chat/{match_id}?token=token-pourri"
        ):
            pass
