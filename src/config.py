"""Configuration defaults for the CircuitGNN pipeline."""
from dataclasses import dataclass
from pathlib import Path

# Device type order is shared across parser/graph/model.
DEVICE_TYPES = ["NMOS", "PMOS", "R", "C"]
# Edge roles for bipartite graph.
EDGE_ROLES = ["D", "G", "S", "B", "P", "N"]
# Special nets for feature one-hot encoding.
SPECIAL_NETS = ["VINP", "VINN", "VOUT", "VDD", "VSS"]

# Score target thresholds used inside utils.compute_score
TARGET_A0_DB = 60.0
TARGET_UGBW_HZ = 1e6
TARGET_PM_DEG = 45.0
TARGET_ID_A = 2e-3


def data_paths(base: Path | str = ".") -> dict[str, Path]:
    """Return common data paths resolved from the project root."""
    root = Path(base).resolve()
    return {
        "generated_netlists": root / "data" / "generated_netlists",
        "spec_csv": root / "data" / "spec_csv",
        "graphs": root / "data" / "graphs",
        "checkpoints": root / "checkpoints",
    }


@dataclass
class TrainingConfig:
    """Hyper-parameters for the multi-task training loop."""

    batch_size: int = 8
    num_epochs: int = 5
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    alpha_mask: float = 1.0
    beta_spec: float = 1.0
    gamma_score: float = 0.5
    lambda_w: float = 0.1
    lambda_l: float = 0.1
    ranking_margin: float = 0.1


@dataclass
class CircuitGNNConfig:
    node_feat_dim: int
    edge_feat_dim: int
    hidden_dim: int = 128
    num_layers: int = 3
    spec_dim: int = 4

