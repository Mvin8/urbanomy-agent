from pathlib import Path
import numpy as np
import pytest
from urbanomy_agent.data import ScenarioRegistry
from urbanomy_agent.engine import execute, project_shares, resolve_bounds
from urbanomy_agent.schemas import LAND_USES
from tests.helpers import Model, optimization

def test_bounded_shares_keep_user_minima():
    shares = project_shares([.2, .9, .9], [.2, 0, 0], [.4, .5, .8])
    assert shares.sum() == pytest.approx(1)
    assert .2 <= shares[0] <= .4
    assert shares[1] <= .5



def test_infeasible_share_bounds_fail_before_search(blocks):
    req = optimization(constraints={"residential": {"min": .9, "max": 1}})
    with pytest.raises(ValueError, match="incompatible"):
        resolve_bounds(req, blocks.iloc[0])



def test_explicit_bounds_can_replace_undefined_baseline(blocks):
    row = blocks.iloc[0].copy()
    for key in LAND_USES:
        row[key] = 0
    row["l"] = np.nan
    req = optimization(constraints={"l": {"min": 1, "max": 3},
                                    **{key: {"min": 0, "max": 1} for key in LAND_USES}})
    bounds = resolve_bounds(req, row)
    assert bounds["l"].max == 3



def test_final_constraints_and_llm_strategy(blocks, monkeypatch):
    from urbanomy.land_value import StrategicAlignmentScorer

    seen = []
    class LLM:
        def invoke(self, prompt):
            seen.append(prompt)
            return {"score": .75}

    monkeypatch.setattr(ScenarioRegistry, "load", lambda *_: (blocks.copy(), Model(), {}))
    monkeypatch.setattr("urbanomy_agent.engine.create_scorer", lambda strategy:
                        (StrategicAlignmentScorer(llm=LLM(), prompt=strategy), "fake-test-model"))
    req = optimization(use_llm=True, constraints={"l": {"min": 2, "max": 6},
                                                "mxi": {"min": .4, "max": .5}})
    result, spatial = execute("optimize_district", req, Path("unused"), lambda _: None)
    assert seen and all("Prefer mixed uses" in prompt for prompt in seen)
    assert result["scenarios"]
    for scenario in result["scenarios"]:
        params = scenario["params_repaired"]
        assert 2 <= params["l"] <= 6
        assert .4 <= params["mxi"] <= .5
        assert sum(params[k] for k in LAND_USES) == pytest.approx(1)
        assert scenario["llm_score"] == .75
    assert len(spatial["features"]) == len(result["scenarios"])
    assert result["provenance"]["llm_model"] == "fake-test-model"



def test_derived_impossible_constraint_never_scores_llm(blocks, monkeypatch):
    from urbanomy.land_value import StrategicAlignmentScorer

    class LLM:
        def invoke(self, _):
            pytest.fail("LLM must not score infeasible candidates")

    monkeypatch.setattr(ScenarioRegistry, "load", lambda *_: (blocks.copy(), Model(), {}))
    monkeypatch.setattr("urbanomy_agent.engine.create_scorer", lambda strategy:
                        (StrategicAlignmentScorer(llm=LLM(), prompt=strategy), "fake"))
    req = optimization(use_llm=True, constraints={"l": {"min": 2, "max": 6}, "mxi": {"min": .9, "max": 1}})
    with pytest.raises(ValueError, match="NO_FEASIBLE_SOLUTION"):
        execute("optimize_district", req, Path("unused"), lambda _: None)



def test_valuation_log_scale_and_context(blocks, monkeypatch):
    from urbanomy_agent.schemas import EstimateRequest

    monkeypatch.setattr(ScenarioRegistry, "load", lambda *_: (blocks.copy(), Model(), {}))
    result, spatial = execute("estimate_land_value", EstimateRequest(scenario_id="test", target_id="0"), Path("unused"), lambda _: None)
    assert result["land_value"] == pytest.approx(8_000_000)
    assert result["land_value_per_sqm"] == pytest.approx(800)
    assert result["dataset_land_value_total"] == pytest.approx(24_000_000)
    assert len(spatial) == 3



def test_profile_resolves_area_and_overrides(blocks):
    req = optimization(constraints_profile="test", constraints={"l": {"min": 3, "max": 4}})
    bounds = resolve_bounds(req, blocks.iloc[0])
    assert bounds["footprint_area"].min == 1
    assert bounds["footprint_area"].max == pytest.approx(.1 * blocks.iloc[0].site_area)
    assert (bounds["l"].min, bounds["l"].max) == (3, 4)
    assert bounds["mxi"].min == .1
    assert all(bounds[k].min == 0 and bounds[k].max == 1 for k in LAND_USES)
    larger = blocks.iloc[0].copy()
    larger["site_area"] *= 2
    assert resolve_bounds(req, larger)["footprint_area"].max == 2 * bounds["footprint_area"].max


def test_profile_request_validation():
    from urbanomy_agent.schemas import OptimizationRequest
    payload = dict(scenario_id="test", target_id=0, strategy="Test")
    for extra in ({}, {"constraints": {}}, {"constraints_profile": "unknown"}):
        with pytest.raises(ValueError):
            OptimizationRequest(**payload, **extra)
    assert OptimizationRequest(**payload, constraints_profile="test").constraints == {}


def test_profile_optimization_enforces_derived_bounds(blocks, monkeypatch):
    monkeypatch.setattr(ScenarioRegistry, "load", lambda *_: (blocks.copy(), Model(), {}))
    req = optimization(constraints_profile="test", constraints={}, pop_size=20, n_gen=3)
    result, _ = execute("optimize_district", req, Path("unused"), lambda _: None)
    assert result["constraints_profile"] == "test"
    assert result["effective_constraints"]["mxi"]["min"] == .1
    for scenario in result["scenarios"]:
        params = scenario["params_repaired"]
        assert .1 - 1e-9 <= params["mxi"] <= 1
        assert 1 <= params["footprint_area"] <= .1 * blocks.iloc[0].site_area
        assert sum(params[k] for k in LAND_USES) == pytest.approx(1)


def test_no_profile_keeps_baseline(blocks):
    bounds = resolve_bounds(optimization(), blocks.iloc[0])
    total = sum(blocks.iloc[0][k] for k in LAND_USES)
    for key in LAND_USES:
        assert bounds[key].min == bounds[key].max == pytest.approx(blocks.iloc[0][key] / total)


def test_profile_small_site_requires_footprint_override(blocks):
    row = blocks.iloc[0].copy()
    row["site_area"] = 5
    with pytest.raises(ValueError):
        resolve_bounds(optimization(constraints_profile="test", constraints={}), row)
    bounds = resolve_bounds(optimization(constraints_profile="test", constraints={
        "footprint_area": {"min": .1, "max": .5}, "mxi": {"min": .2, "max": .7}}), row)
    assert bounds["footprint_area"].max == .5
    assert bounds["mxi"].min == .2


def test_a2a_profile_without_constraints():
    from a2a.types import Message
    from google.protobuf.json_format import ParseDict
    from urbanomy_agent.a2a import parse_input
    message = ParseDict({"messageId": "profile", "role": "ROLE_USER", "parts": [{"data": {
        "operation": "optimize_district", "scenario_id": "test", "target_id": "0",
        "strategy": "Test", "constraints_profile": "test", "use_llm": False}}]}, Message())
    operation, payload = parse_input(message)
    assert operation == "optimize_district"
    assert payload["constraints_profile"] == "test"
    assert payload["constraints"] == {}


def test_project_label_is_provenance_only(blocks, monkeypatch):
    from urbanomy_agent.schemas import EstimateRequest
    seen = []
    def load(_registry, scenario):
        seen.append(scenario)
        return blocks.copy(), Model(), {}
    monkeypatch.setattr(ScenarioRegistry, "load", load)
    result, _ = execute("estimate_land_value", EstimateRequest(scenario_id="test", target_id=0,
                        project_id="project-1"), Path("unused"), lambda _: None)
    assert seen == ["test"]
    assert result["provenance"]["scenario_id"] == "test"
    assert result["provenance"]["project_id"] == "project-1"
