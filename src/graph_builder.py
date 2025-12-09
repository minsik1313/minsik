"""Convert netlists to bipartite PyTorch Geometric graphs."""
from __future__ import annotations

from typing import Dict, List

import torch
from torch import Tensor
from torch_geometric.data import Data

from config import DEVICE_TYPES, EDGE_ROLES, SPECIAL_NETS
from netlist_parser import Device, Netlist
from utils import safe_log10


class GraphBuilder:
    """Build bipartite graphs from parsed netlists."""

    def __init__(self, device_types: List[str] | None = None) -> None:
        self.device_types = device_types or DEVICE_TYPES
        self.edge_roles = EDGE_ROLES
        self.special_nets = SPECIAL_NETS
        self.device_feature_dim = len(self.device_types) + 5
        self.net_feature_dim = len(self.special_nets) + 1
        self.node_feature_dim = max(self.device_feature_dim, self.net_feature_dim)

    def build_graph(self, netlist: Netlist) -> Data:
        net_indices: Dict[str, int] = {}
        device_indices: Dict[str, int] = {}
        nodes: List[Tensor] = []
        node_type: List[int] = []
        net_names: List[str] = []

        # Net nodes
        for idx, net in enumerate(sorted(netlist.nets)):
            net_indices[net] = idx
            net_names.append(net)
            nodes.append(self._net_features(net))
            node_type.append(0)

        # Device nodes
        for device in netlist.devices:
            device_idx = len(nodes)
            device_indices[device.name] = device_idx
            nodes.append(self._device_features(device))
            node_type.append(1)

        edge_list: List[List[int]] = []
        edge_attrs: List[Tensor] = []

        for device in netlist.devices:
            dev_idx = device_indices[device.name]
            for pin_idx, net_name in enumerate(device.nodes):
                if net_name not in net_indices:
                    continue
                net_idx = net_indices[net_name]
                edge_list.append([dev_idx, net_idx])
                edge_list.append([net_idx, dev_idx])
                role_feature = self._edge_feature(device.dev_type, pin_idx)
                edge_attrs.append(role_feature)
                edge_attrs.append(role_feature)

        x = torch.stack(nodes, dim=0)
        edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()
        edge_attr = torch.stack(edge_attrs, dim=0)

        data = Data(
            x=x,
            edge_index=edge_index,
            edge_attr=edge_attr,
            node_type=torch.tensor(node_type, dtype=torch.long),
        )
        data.net_names = net_names
        data.device_indices = device_indices
        return data

    def _net_features(self, net: str) -> Tensor:
        feats = [1.0 if net.upper() == s else 0.0 for s in self.special_nets]
        # internal flag
        feats.append(0.0 if any(feats) else 1.0)
        while len(feats) < self.node_feature_dim:
            feats.append(0.0)
        return torch.tensor(feats, dtype=torch.float)

    def _device_features(self, device: Device) -> Tensor:
        type_one_hot = [1.0 if device.dev_type == t else 0.0 for t in self.device_types]
        params = device.params
        w = safe_log10(params.get("W", 0.0))
        l = safe_log10(params.get("L", 0.0))
        m = params.get("M", 0.0)
        r_value = safe_log10(params.get("R", 0.0))
        c_value = safe_log10(params.get("C", 0.0))
        feats = type_one_hot + [w, l, m, r_value, c_value]
        while len(feats) < self.node_feature_dim:
            feats.append(0.0)
        return torch.tensor(feats, dtype=torch.float)

    def _edge_feature(self, dev_type: str, pin_idx: int) -> Tensor:
        role_one_hot = [0.0 for _ in self.edge_roles]
        if dev_type in {"NMOS", "PMOS"}:
            role = ["D", "G", "S", "B"][pin_idx]
        else:
            role = ["P", "N"][pin_idx]
        if role in self.edge_roles:
            role_one_hot[self.edge_roles.index(role)] = 1.0
        return torch.tensor(role_one_hot, dtype=torch.float)


__all__ = ["GraphBuilder"]

