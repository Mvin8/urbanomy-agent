import pytest
from a2a.types import Message
from google.protobuf.json_format import ParseDict
from pydantic import ValidationError
from urbanomy_agent.a2a import parse_input
from urbanomy_agent.schemas import OptimizationRequest
from tests.helpers import request


@pytest.mark.parametrize("change", [
    {"constraints": {"l": {"min": 9, "max": 8}}},
    {"constraints": {"unknown": {"min": 1, "max": 8}}},
    {"constraints": {"l": {"min": 1, "max": float('inf')}}},
    {"constraints": {"recreation": {"min": 0, "max": 20}}},
    {"scenario_id": "../private"}, {"target_id": True}, {"strategy": " "}, {"n_gen": 0},
])
def test_invalid_inputs(change):
    payload = request().model_dump()
    payload.update(change)
    with pytest.raises(ValidationError):
        OptimizationRequest.model_validate(payload)



def test_prompt_alias_and_structured_precedence():
    message = ParseDict({"messageId": "1", "role": "ROLE_USER", "parts": [
        {"text": "different strategy"}, {"data": {"operation": "optimize_district", "scenario_id": "test", "target_id": 86,
        "prompt": "explicit strategy", "constraints_json": '{"l":{"min":1,"max":8}}', "n_gen": 1}},
    ]}, Message())
    _, payload = parse_input(message)
    assert payload["strategy"] == "explicit strategy"
    assert payload["target_id"] == 86
    assert payload["n_gen"] == 1


@pytest.mark.parametrize("parts", [
    [{"data": {"operation": "optimize_district", "constraints": {}, "constraints_json": "{}"}}],
    [{"data": {"operation": "optimize_district", "constraints_json": "not-json"}}],
    [{"data": {"operation": "estimate_land_value"}}, {"data": {"operation": "optimize_district"}}],
    [{"data": [1, 2]}],
    [{"url": "https://example.invalid/data.geojson"}],
    [{"data": {"operation": "optimize_district", "scenario_id": "test", "target_id": 1, "unknown": True}}],
])
def test_invalid_a2a_parts_are_rejected(parts):
    message = ParseDict({"messageId": "1", "role": "ROLE_USER", "parts": parts}, Message())
    with pytest.raises((ValueError, TypeError)):
        parse_input(message)


def test_text_is_strategy_only_when_structured_strategy_is_absent():
    payload = request().model_dump()
    payload.pop("strategy")
    message = ParseDict({"messageId": "1", "role": "ROLE_USER", "parts": [
        {"text": "Keep mixed uses"}, {"data": {"operation": "optimize_district", **payload}}]}, Message())
    operation, parsed = parse_input(message)
    assert operation == "optimize_district"
    assert parsed["strategy"] == "Keep mixed uses"


def test_conflicting_prompt_aliases_are_not_silently_chosen():
    payload = request().model_dump()
    payload["prompt"] = "Different strategy"
    with pytest.raises(ValidationError):
        OptimizationRequest.model_validate(payload)


def test_old_dataset_field_is_rejected():
    from urbanomy_agent.schemas import EstimateRequest
    with pytest.raises(ValidationError):
        EstimateRequest.model_validate({"dataset_id": "baseline", "target_id": 86})


def test_a2a_scenario_and_project_label():
    message = ParseDict({"messageId": "scenario", "role": "ROLE_USER", "parts": [{"data": {
        "operation": "estimate_land_value", "scenario_id": "test", "target_id": "0",
        "project_id": "project-1"}}]}, Message())
    _, payload = parse_input(message)
    assert payload["scenario_id"] == "test"
    assert payload["project_id"] == "project-1"
