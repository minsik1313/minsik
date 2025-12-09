"""Multi-task training loop for the CircuitGNN surrogate model."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple

import torch
from torch import nn
from torch_geometric.loader import DataLoader

from config import CircuitGNNConfig, DEVICE_TYPES, TrainingConfig
from data_generator import DataGenerator
from dataset import CircuitGraphDataset
from model import CircuitSurrogate


def ranking_loss(score_pred: torch.Tensor, pairs: List[Tuple[int, int]], margin: float) -> torch.Tensor:
    if not pairs:
        return torch.tensor(0.0, device=score_pred.device)
    losses = []
    for i, j in pairs:
        diff = score_pred[i] - score_pred[j]
        losses.append(torch.relu(margin - diff))
    return torch.stack(losses).mean()


def train(
    base_netlists: List[str],
    training_cfg: TrainingConfig,
    device: str = "cpu",
) -> None:
    generator = DataGenerator(base_netlists)
    data_list, ranking_pairs = generator.generate()

    dataset = CircuitGraphDataset(data_list)
    loader = DataLoader(dataset, batch_size=training_cfg.batch_size, shuffle=True)

    sample = data_list[0]
    config = CircuitGNNConfig(
        node_feat_dim=sample.x.size(1),
        edge_feat_dim=sample.edge_attr.size(1),
        hidden_dim=128,
        num_layers=3,
    )
    model = CircuitSurrogate(config, num_dev_types=len(DEVICE_TYPES)).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=training_cfg.learning_rate, weight_decay=training_cfg.weight_decay)
    mse_loss = nn.MSELoss()
    ce_loss = nn.CrossEntropyLoss()

    ranking_lookup = {(i, j) for i, j in ranking_pairs}

    for epoch in range(training_cfg.num_epochs):
        model.train()
        total_loss = 0.0
        for data in loader:
            data = data.to(device)
            node_emb, graph_emb = model.gnn(data)

            # Mask losses
            mask_idx = data.mask_device_idx
            mask_type_label = data.mask_type_label
            mask_w_label = data.mask_W_label
            mask_l_label = data.mask_L_label

            valid_mask = mask_idx >= 0
            mask_loss = torch.tensor(0.0, device=device)
            if valid_mask.any():
                type_logits, w_pred, l_pred = model.mask_head(node_emb, mask_idx[valid_mask])
                mask_loss = ce_loss(type_logits, mask_type_label[valid_mask])
                mask_loss += training_cfg.lambda_w * mse_loss(w_pred, mask_w_label[valid_mask])
                mask_loss += training_cfg.lambda_l * mse_loss(l_pred, mask_l_label[valid_mask])

            # Spec regression
            y_spec_pred = model.spec_head(graph_emb)
            spec_loss = mse_loss(y_spec_pred, data.y_spec)

            # Score regression
            score_pred = model.score_head(graph_emb)
            score_loss = mse_loss(score_pred, data.score.squeeze(-1))

            # Ranking loss for pairs within the current batch
            batch_indices = data.graph_idx
            batch_map = {int(idx): pos for pos, idx in enumerate(batch_indices.tolist())}
            batch_pairs = [(batch_map[i], batch_map[j]) for i, j in ranking_lookup if i in batch_map and j in batch_map]
            rank_loss = torch.tensor(0.0, device=device)
            if batch_pairs:
                rank_loss = ranking_loss(score_pred, batch_pairs, margin=training_cfg.ranking_margin)

            loss = training_cfg.alpha_mask * mask_loss + training_cfg.beta_spec * spec_loss + training_cfg.gamma_score * (score_loss + rank_loss)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        avg_loss = total_loss / max(1, len(loader))
        print(f"Epoch {epoch+1}/{training_cfg.num_epochs} - Loss: {avg_loss:.4f}")

    ckpt_path = Path("checkpoints") / "circuitgnn_latest.pt"
    ckpt_path.parent.mkdir(exist_ok=True, parents=True)
    torch.save(model.state_dict(), ckpt_path)
    print(f"Saved checkpoint to {ckpt_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train CircuitGNN multi-task model")
    parser.add_argument("--netlists", nargs="*", default=[
        "netlists/amp1.cir",
        "netlists/amp2.cir",
        "netlists/amp3.cir",
        "netlists/amp4.cir",
    ])
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", type=str, default="cpu")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    training_cfg = TrainingConfig(batch_size=args.batch, num_epochs=args.epochs)
    train(args.netlists, training_cfg, device=args.device)

