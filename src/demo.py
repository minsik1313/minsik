"""Run a quick demo inference for a given amplifier netlist."""
from __future__ import annotations

import argparse
from pathlib import Path

import torch

from config import CircuitGNNConfig, DEVICE_TYPES
from graph_builder import GraphBuilder
from model import CircuitSurrogate
from netlist_parser import NetlistParser


def run_demo(netlist_path: str, checkpoint: str, device: str = "cpu") -> None:
    parser = NetlistParser()
    builder = GraphBuilder()

    netlist = parser.parse_file(netlist_path)
    data = builder.build_graph(netlist)
    data = data.to(device)

    config = CircuitGNNConfig(
        node_feat_dim=data.x.size(1),
        edge_feat_dim=data.edge_attr.size(1),
        hidden_dim=128,
        num_layers=3,
    )
    model = CircuitSurrogate(config, num_dev_types=len(DEVICE_TYPES)).to(device)

    ckpt_path = Path(checkpoint)
    if ckpt_path.exists():
        state = torch.load(ckpt_path, map_location=device)
        model.load_state_dict(state)
    model.eval()

    with torch.no_grad():
        node_emb, graph_emb = model.gnn(data)
        spec_pred = model.spec_head(graph_emb)
        score_pred = model.score_head(graph_emb)

    result = {
        "A0_db_pred": float(spec_pred[0, 0].item()),
        "UGBW_Hz_pred": float(spec_pred[0, 1].item()),
        "PM_deg_pred": float(spec_pred[0, 2].item()),
        "ID_A_pred": float(spec_pred[0, 3].item()),
        "score_pred": float(score_pred[0].item()),
    }
    print("Predictions for", netlist_path)
    for k, v in result.items():
        print(f"  {k}: {v}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CircuitGNN demo")
    parser.add_argument("--netlist", type=str, required=True)
    parser.add_argument("--checkpoint", type=str, default="checkpoints/circuitgnn_latest.pt")
    parser.add_argument("--device", type=str, default="cpu")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_demo(args.netlist, args.checkpoint, device=args.device)

