"""One validated input contract shared by both transports."""
from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

BlockId = StrictInt | StrictStr
ScenarioId = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")]
LAND_USES = ("residential", "business", "recreation", "industrial", "transport", "special", "agriculture")
INDEPENDENT = ("footprint_area", "l", *LAND_USES)
DERIVED = ("mxi", "fsi", "gsi", "build_floor_area", "living_area", "non_living_area", "population")


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class Bounds(InputModel):
    min: float
    max: float
    type: Literal["float"] = "float"

    @model_validator(mode="after")
    def ordered(self):
        if self.min < 0 or self.min > self.max:
            raise ValueError("Bounds require 0 <= min <= max.")
        return self


class EstimateRequest(InputModel):
    scenario_id: ScenarioId
    target_id: BlockId
    project_id: ScenarioId | None = None


class OptimizationRequest(EstimateRequest):
    constraints: dict[str, Bounds] = Field(default_factory=dict)
    constraints_profile: Literal["test"] | None = None
    strategy: str = Field(min_length=1, max_length=12000, validation_alias=AliasChoices("strategy", "prompt"))
    use_llm: bool = True
    pop_size: int = Field(default=20, ge=4, le=100, strict=True)
    n_gen: int = Field(default=20, ge=1, le=200, strict=True)
    seed: int = Field(default=42, ge=0, le=2**32 - 1, strict=True)

    @model_validator(mode="after")
    def known_constraints(self):
        if not self.constraints and self.constraints_profile is None:
            raise ValueError("Provide non-empty constraints or constraints_profile.")
        unknown = self.constraints.keys() - set(INDEPENDENT + DERIVED)
        if unknown:
            raise ValueError(f"Unsupported constraints: {sorted(unknown)}")
        for name, bounds in self.constraints.items():
            if name in (*LAND_USES, "mxi", "gsi") and bounds.max > 1:
                raise ValueError(f"{name} is a fraction in [0, 1].")
            if name == "l" and bounds.min < 1:
                raise ValueError("l is average floors and must be >= 1 (not necessarily integer).")
        return self
