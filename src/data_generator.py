"""Dataset generation utilities: mutate netlists, run ngspice, and build graphs."""
from __future__ import annotations

import copy
import random
from pathlib import Path
from typing import Dict, List, Tuple

import torch
from torch_geometric.data import Data

from config import DEVICE_TYPES, data_paths
from graph_builder import GraphBuilder
from netlist_parser import Netlist, NetlistParser
from ngspice_runner import NgspiceRunner
from utils import append_spec_to_csv, compute_score


class DataGenerator:
    """Generate graph datasets from base amplifier netlists."""

    def __init__(
        self,
        base_netlist_paths: List[str],
        output_root: str | Path = ".",
        num_variants: int = 20,
        rng_seed: int = 0,
    ) -> None:
        self.base_netlist_paths = base_netlist_paths
        self.output_root = Path(output_root)
        self.num_variants = num_variants
        self.rng = random.Random(rng_seed)
        self.parser = NetlistParser()
        self.builder = GraphBuilder()
        self.runner = NgspiceRunner()
        self.paths = data_paths(self.output_root)

    def generate(self) -> Tuple[List[Data], List[Tuple[int, int]]]:
        data_list: List[Data] = []
        ranking_pairs: List[Tuple[int, int]] = []
        base_indices: Dict[str, List[int]] = {}

        for base_path in self.base_netlist_paths:
            base_name = Path(base_path).stem
            netlist = self.parser.parse_file(base_path)
            netlists_to_run: List[Tuple[str, Netlist]] = [(f"{base_name}_orig", netlist)]
            netlists_to_run += self._create_variants(netlist, base_name)

            for net_id, nl in netlists_to_run:
                file_path = self.paths["generated_netlists"] / f"{net_id}.cir"
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(self._serialize_netlist(nl), encoding="utf-8")

                spec = self.runner.run_ac_analysis(str(file_path))
                append_spec_to_csv(self.paths["spec_csv"] / "specs.csv", net_id, spec)
                score = compute_score(spec)

                data = self.builder.build_graph(nl)
                graph_idx = len(data_list)
                self._attach_targets(data, nl, score, spec, net_id)
                data.graph_idx = graph_idx
                data_list.append(data)
                base_indices.setdefault(base_name, []).append(graph_idx)

        # ranking pairs per base
        for indices in base_indices.values():
            if not indices:
                continue
            scores = [(idx, float(data_list[idx].score.item())) for idx in indices]
            scores.sort(key=lambda x: x[1], reverse=True)
            k = max(1, len(scores) // 4)
            good = [idx for idx, _ in scores[:k]]
            bad = [idx for idx, _ in scores[-k:]]
            for g in good:
                for b in bad:
                    if g != b:
                        ranking_pairs.append((g, b))

        graphs_path = self.paths["graphs"] / "dataset.pt"
        graphs_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(data_list, graphs_path)
        torch.save(ranking_pairs, self.paths["graphs"] / "ranking_pairs.pt")
        return data_list, ranking_pairs

    def _create_variants(self, netlist: Netlist, base_name: str) -> List[Tuple[str, Netlist]]:
        variants: List[Tuple[str, Netlist]] = []
        for i in range(self.num_variants):
            variant = copy.deepcopy(netlist)
            variant_id = f"{base_name}_var{i:03d}"
            choice = self.rng.choice(["remove", "scale_mos", "scale_passive"])
            if choice == "remove":
                self._remove_device(variant)
            elif choice == "scale_mos":
                self._scale_mos(variant)
            else:
                self._scale_passive(variant)
            variants.append((variant_id, variant))
        return variants

    def _remove_device(self, netlist: Netlist) -> None:
        mos_devices = [d for d in netlist.devices if d.dev_type in {"NMOS", "PMOS"}]
        if not mos_devices:
            return
        device = self.rng.choice(mos_devices)
        netlist.devices.remove(device)

    def _scale_mos(self, netlist: Netlist) -> None:
        mos_devices = [d for d in netlist.devices if d.dev_type in {"NMOS", "PMOS"}]
        if not mos_devices:
            return
        device = self.rng.choice(mos_devices)
        s_w = self.rng.uniform(0.5, 2.0)
        s_l = self.rng.uniform(0.5, 2.0)
        if "W" in device.params:
            device.params["W"] *= s_w
        if "L" in device.params:
            device.params["L"] *= s_l

    def _scale_passive(self, netlist: Netlist) -> None:
        passives = [d for d in netlist.devices if d.dev_type in {"R", "C"}]
        if not passives:
            return
        device = self.rng.choice(passives)
        scale = self.rng.uniform(0.5, 2.0)
        key = "R" if device.dev_type == "R" else "C"
        if key in device.params:
            device.params[key] *= scale

    def _serialize_netlist(self, netlist: Netlist) -> str:
        lines: List[str] = []
        for device in netlist.devices:
            if device.dev_type in {"NMOS", "PMOS"}:
                model_token = "nmos" if device.dev_type == "NMOS" else "pmos"
                params = " ".join(f"{k}={v}" for k, v in device.params.items())
                line = f"{device.name} {' '.join(device.nodes)} {model_token} {params}".strip()
            elif device.dev_type == "R":
                value = device.params.get("R", 0.0)
                line = f"{device.name} {device.nodes[0]} {device.nodes[1]} {value}"
            else:
                value = device.params.get("C", 0.0)
                line = f"{device.name} {device.nodes[0]} {device.nodes[1]} {value}"
            lines.append(line)
        lines.append(".end")
        return "\n".join(lines)

    def _attach_targets(self, data: Data, netlist: Netlist, score: float, spec: Dict[str, float], netlist_id: str) -> None:
        data.y_spec = torch.tensor(
            [spec.get("A0_db", 0.0), spec.get("UGBW_Hz", 0.0), spec.get("PM_deg", 0.0), spec.get("ID_A", 0.0)],
            dtype=torch.float,
        )
        data.score = torch.tensor([score], dtype=torch.float)
        data.netlist_id = netlist_id

        device_nodes = [idx for idx, t in enumerate(data.node_type.tolist()) if t == 1]
        if not device_nodes or not netlist.devices:
            data.mask_device_idx = torch.tensor(-1, dtype=torch.long)
            data.mask_type_label = torch.tensor(-1, dtype=torch.long)
            data.mask_W_label = torch.tensor(0.0)
            data.mask_L_label = torch.tensor(0.0)
            return

        mask_idx = self.rng.choice(device_nodes)
        data.mask_device_idx = torch.tensor(mask_idx, dtype=torch.long)
        data.x[mask_idx] = 0.0

        device_name = None
        for name, idx in data.device_indices.items():
            if idx == mask_idx:
                device_name = name
                break
        if device_name is None:
            device = netlist.devices[0]
        else:
            device = next((d for d in netlist.devices if d.name == device_name), netlist.devices[0])

        type_label = DEVICE_TYPES.index(device.dev_type) if device.dev_type in DEVICE_TYPES else -1
        data.mask_type_label = torch.tensor(type_label, dtype=torch.long)
        data.mask_W_label = torch.tensor(float(device.params.get("W", 0.0)), dtype=torch.float)
        data.mask_L_label = torch.tensor(float(device.params.get("L", 0.0)), dtype=torch.float)


__all__ = ["DataGenerator"]

