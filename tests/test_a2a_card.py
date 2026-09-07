from dataclasses import replace

from fastapi.testclient import TestClient
from google.protobuf.json_format import MessageToDict

from urbanomy_agent.a2a import build_card
from urbanomy_agent.server import build_app


def test_public_url_and_skills_match_the_served_card(settings):
    settings = replace(settings, public_url="https://urbanomy.example/service/")
    card = MessageToDict(build_card(settings))
    with TestClient(build_app(settings)) as client:
        assert client.get("/.well-known/agent-card.json").json() == card
    assert card["supportedInterfaces"] == [{"url": "https://urbanomy.example/service/a2a",
                                          "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}]
    assert {s["id"] for s in card["skills"]} == {"estimate_land_value", "optimize_district"}
    assert {"protocolVersion", "url", "preferredTransport"}.isdisjoint(card)
    extension = card["capabilities"]["extensions"][0]
    assert extension["required"]
    assert extension["params"]["properties"]["constraints_json"]["type"] == "string"


def test_bearer_card_announces_auth_without_disclosing_credentials(settings):
    settings = replace(settings, token="private-test-credential")
    card = MessageToDict(build_card(settings))
    assert card["securitySchemes"]["bearer"]["httpAuthSecurityScheme"]["scheme"] == "bearer"
    assert card["securityRequirements"]
    assert settings.token not in str(card)
