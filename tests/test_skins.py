from fastapi.testclient import TestClient

from tests.utils import dict_without_key
import metaserver.database.api as db
import metaserver.database.models as models


def test_user_skins(client: TestClient):
    # Register a new user.
    user_auth = ("foo@example.com", "12345678")
    user = client.post(
        "/v1/user/register",
        json=dict(username=user_auth[0], display_name="foo", password=user_auth[1]),
    ).json()

    # Add skin for user
    session = next(db.get_session())
    user_obj = db.get_user_by_id(session, user["id"])
    kind, unit, model_path = "shield", "lego", "one/two/three/legoshield.model"
    skin = models.Skin(
        kind=kind,
        unit=unit,
        model_path=model_path,
    )
    link = models.UserSkinLink(user=user_obj, skin=skin)
    session.add(link)
    session.commit()

    # Check that we're getting it back from the route.
    response = client.get(
        "/v1/skin/for-user/by-id", json=dict(user_id=user["id"]), auth=user_auth
    )
    assert dict_without_key(response.json()[0], "id") == dict(
        description=None, kind=kind, unit=unit, model_path=model_path
    )


def test_clan_skins(client: TestClient):
    # Register a new user.
    user_auth = ("foo@example.com", "12345678")
    user = client.post(
        "/v1/user/register",
        json=dict(username=user_auth[0], display_name="foo", password=user_auth[1]),
    ).json()

    # Let them create a clan.
    clan_name, clan_tag = "Zaitev's Snore Club", "Zzz"
    clan = client.post(
        "/v1/clan/register",
        json=dict(tag=clan_tag, name=clan_name),
        auth=user_auth,
    ).json()

    # Add skin for clan
    session = next(db.get_session())
    clan_obj = db.get_clan_by_id(session, clan["id"])
    kind, unit, model_path = "shield", "lego", "one/two/three/legoshield.model"
    skin = models.Skin(
        kind=kind,
        unit=unit,
        model_path=model_path,
    )
    link = models.ClanSkinLink(clan=clan_obj, skin=skin)
    session.add(link)
    session.commit()

    # Check that we're getting it back from the route.
    response = client.get(
        "/v1/skin/for-clan/by-id", json=dict(clan_id=clan["id"]), auth=user_auth
    )
    assert dict_without_key(response.json()[0], "id") == dict(
        description=None, kind=kind, unit=unit, model_path=model_path
    )
