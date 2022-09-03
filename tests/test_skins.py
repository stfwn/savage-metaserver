from fastapi.testclient import TestClient

import metaserver.database.api as db
import metaserver.database.models as models
from tests.utils import dict_without_key


def test_user_skins(client: TestClient, user: dict):
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
        "/v1/skin/for-user/by-id", params=dict(user_id=user["id"]), auth=user["auth"]
    )
    assert dict_without_key(response.json()[0], "id") == dict(
        description=None, kind=kind, unit=unit, model_path=model_path
    )


def test_clan_skins(client: TestClient, user: dict, clan_icon: str):
    # Create a clan.
    clan_name, clan_tag = "Zaitev's Snore Club", "Zzz"
    clan = client.post(
        "/v1/clan/register",
        json=dict(tag=clan_tag, name=clan_name, icon=clan_icon),
        auth=user["auth"],
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

    # Check that we're getting it back from the clan route.
    response = client.get(
        "/v1/skin/for-clan/by-id",
        params=dict(clan_id=clan["id"]),
        auth=user["auth"],
    )
    assert dict_without_key(response.json()[0], "id") == dict(
        description=None, kind=kind, unit=unit, model_path=model_path
    )

    # Check that we're getting it back from the user route if we ask for it.
    response = client.get(
        "/v1/skin/for-user/by-id",
        params=dict(user_id=user["id"], clan_id=clan["id"]),
        auth=user["auth"],
    )
    assert dict_without_key(response.json()[0], "id") == dict(
        description=None, kind=kind, unit=unit, model_path=model_path
    )

    # Check that we're not getting it back from the user route if we don't ask.
    response = client.get(
        "/v1/skin/for-user/by-id",
        params=dict(user_id=user["id"]),
        auth=user["auth"],
    )
    assert response.json() == []
