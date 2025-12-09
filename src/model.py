"""CircuitGNN and task heads."""
from __future__ import annotations

import torch
from torch import nn
from torch_geometric.nn import GCNConv, global_mean_pool

from config import CircuitGNNConfig


class CircuitGNN(nn.Module):
    """Simple GCN-based encoder for circuit graphs."""

    def __init__(self, config: CircuitGNNConfig):
        super().__init__()
        self.config = config
        self.convs = nn.ModuleList()
        self.bns = nn.ModuleList()

        in_dim = config.node_feat_dim
        for _ in range(config.num_layers):
            conv = GCNConv(in_dim, config.hidden_dim)
            self.convs.append(conv)
            self.bns.append(nn.BatchNorm1d(config.hidden_dim))
            in_dim = config.hidden_dim

    def forward(self, data):
        x, edge_index = data.x, data.edge_index
        for conv, bn in zip(self.convs, self.bns):
            x = conv(x, edge_index)
            x = bn(x)
            x = torch.relu(x)

        batch = getattr(data, "batch", torch.zeros(x.size(0), dtype=torch.long, device=x.device))
        graph_embedding = global_mean_pool(x, batch)
        return x, graph_embedding


class MaskHead(nn.Module):
    """Predict device type and sizes for masked nodes."""

    def __init__(self, hidden_dim: int, num_dev_types: int):
        super().__init__()
        self.type_fc = nn.Linear(hidden_dim, num_dev_types)
        self.w_fc = nn.Linear(hidden_dim, 1)
        self.l_fc = nn.Linear(hidden_dim, 1)

    def forward(self, node_embeddings, mask_idx):
        masked_emb = node_embeddings[mask_idx]
        type_logits = self.type_fc(masked_emb)
        w_pred = self.w_fc(masked_emb).squeeze(-1)
        l_pred = self.l_fc(masked_emb).squeeze(-1)
        return type_logits, w_pred, l_pred


class SpecHead(nn.Module):
    """Predict circuit specs from graph embeddings."""

    def __init__(self, hidden_dim: int, spec_dim: int):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, spec_dim),
        )

    def forward(self, graph_emb):
        return self.mlp(graph_emb)


class ScoreHead(nn.Module):
    """Predict scalar quality score from graph embeddings."""

    def __init__(self, hidden_dim: int):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, graph_emb):
        return self.mlp(graph_emb).squeeze(-1)


class CircuitSurrogate(nn.Module):
    """Wrapper containing encoder and all task heads."""

    def __init__(self, config: CircuitGNNConfig, num_dev_types: int):
        super().__init__()
        self.gnn = CircuitGNN(config)
        self.mask_head = MaskHead(config.hidden_dim, num_dev_types)
        self.spec_head = SpecHead(config.hidden_dim, config.spec_dim)
        self.score_head = ScoreHead(config.hidden_dim)

    def forward(self, data):
        return self.gnn(data)


__all__ = ["CircuitGNN", "CircuitSurrogate", "MaskHead", "SpecHead", "ScoreHead"]

