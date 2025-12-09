"""Simple Dataset wrapper for PyG Data objects."""
from __future__ import annotations

from typing import List

from torch.utils.data import Dataset
from torch_geometric.data import Data


class CircuitGraphDataset(Dataset):
    """Wrap a list of PyG Data objects for DataLoader compatibility."""

    def __init__(self, data_list: List[Data]):
        self.data_list = data_list

    def __len__(self) -> int:
        return len(self.data_list)

    def __getitem__(self, idx: int) -> Data:
        return self.data_list[idx]


__all__ = ["CircuitGraphDataset"]

