#!/usr/bin/env bash
# Codespaces / devcontainer bootstrap: install the open-source EDA tools the
# demo flow needs. See docs/SETUP.md for the full (PDK-enabled) container.
set -e

sudo apt-get update
sudo apt-get install -y iverilog ngspice
pip install cocotb

echo
echo "Bootstrap complete. Verify the flow with:"
echo "  make digital-sim       # cocotb + Icarus regression"
echo "  make analog-autosize   # voltage-domain-aware analog sizing"
