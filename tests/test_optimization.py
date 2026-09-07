from pathlib import Path
import numpy as np
import pytest
from urbanomy_agent.data import DatasetRegistry
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

    monkeypatch.setattr(DatasetRegistry, "load", lambda *_: (blocks.copy(), Model(), {}))
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

    monkeypatch.setattr(DatasetRegistry, "load", lambda *_: (blocks.copy(), Model(), {}))
    monkeypatch.setattr("urbanomy_agent.engine.create_scorer", lambda strategy:
                        (StrategicAlignmentScorer(llm=LLM(), prompt=strategy), "fake"))
    req = optimization(use_llm=True, constraints={"l": {"min": 2, "max": 6}, "mxi": {"min": .9, "max": 1}})
    with pytest.raises(ValueError, match="NO_FEASIBLE_SOLUTION"):
        execute("optimize_district", req, Path("unused"), lambda _: None)



def test_valuation_log_scale_and_context(blocks, monkeypatch):
    from urbanomy_agent.schemas import EstimateRequest

    monkeypatch.setattr(DatasetRegistry, "load", lambda *_: (blocks.copy(), Model(), {}))
    result, spatial = execute("estimate_land_value", EstimateRequest(dataset_id="test", target_id="0"), Path("unused"), lambda _: None)
    assert result["land_value"] == pytest.approx(8_000_000)
    assert result["land_value_per_sqm"] == pytest.approx(800)
    assert result["dataset_land_value_total"] == pytest.approx(24_000_000)
    assert len(spatial) == 3

