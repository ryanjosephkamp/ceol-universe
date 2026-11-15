"""The study kit of the CEOL Universe, for version 1.0 of the dataset.

    from ceolkit import load, draw, strata

    universe = load("universe", "v1.0", source="path/to/data")
    sample, manifest = draw(universe, strata.evidence_tier, 100, "my-seed")

`load` reads a config at a pinned version, `draw` draws a deterministic
stratified sample and records its manifest, and `strata` holds the ready
strata. See `kit/README.md`.
"""

__version__ = "1.0"

from . import strata  # noqa: E402
from .load import (CONFIGS, DATASET, DATASET_VERSION, figure, figures,  # noqa: E402
                   hub_path, join_features, load)
from .sample import RULE, draw, label_text, rank_key  # noqa: E402
from .strata import (STRATA, Stratum, combine, evidence_tier,  # noqa: E402
                     family_cells, frequency_band, intake_layer, length_band,
                     model_or_engine, spelling_class)

__all__ = [
    "CONFIGS", "DATASET", "DATASET_VERSION", "RULE", "STRATA", "Stratum",
    "combine", "draw", "evidence_tier", "family_cells", "figure", "figures",
    "frequency_band", "hub_path", "intake_layer", "join_features",
    "label_text", "length_band", "load", "model_or_engine", "rank_key",
    "spelling_class", "strata",
]
