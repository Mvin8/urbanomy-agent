"""Server-side optimization presets. Fractions of site area resolve per block."""
from .schemas import LAND_USES, Bounds

TEST_PROFILE = {
    "footprint_area": {"min": 1.0, "max_site_area_fraction": 0.1},
    "l": {"min": 1.0, "max": 10.0},
    "mxi": {"min": 0.1, "max": 1.0},
    **{key: {"min": 0.0, "max": 1.0} for key in LAND_USES},
}


def profile_constraints(name, site_area, overrides):
    if name is None:
        return dict(overrides)
    if name != "test":
        raise ValueError(f"Unknown constraints profile: {name}")
    resolved = {}
    for key, config in TEST_PROFILE.items():
        if key in overrides:
            continue
        maximum = (config["max_site_area_fraction"] * float(site_area)
                   if "max_site_area_fraction" in config else config["max"])
        resolved[key] = Bounds(min=config["min"], max=maximum)
    return {**resolved, **overrides}
