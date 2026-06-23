#!/usr/bin/env bash
# Run the sky130 sub-1V bandgap testbenches (TC, startup, line regulation).
#
# Requires: ngspice + the sky130A PDK ngspice models.
# Install the PDK once with volare (any writable PDK_ROOT):
#   pip install volare
#   export PDK_ROOT=$HOME/.volare
#   volare enable --pdk sky130 c6d73a35f524070e85faff4a6a9eef49553ebc2b
set -euo pipefail
cd "$(dirname "$0")"

PDK_ROOT="${PDK_ROOT:-$HOME/.volare}"
LIB="$PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice"
if [[ ! -f "$LIB" ]]; then
  echo "ERROR: sky130 models not found at $LIB"
  echo "Set PDK_ROOT or install via volare (see header of this script)."
  exit 1
fi

# pdk.spice is generated so the testbenches stay PDK-path agnostic.
printf '.lib "%s" tt\n' "$LIB" > pdk.spice

echo "==> TC (Vref vs temperature)"
ngspice -b tb_tc.spice 2>&1 | awk '
/^TCPT/ {t=$2; v=$3; printf "    %5sC : %s V\n", t, v;
         if(n++==0||v>mx)mx=v; if(n==1||v<mn)mn=v; s+=v; if(t==27)v27=v}
END {avg=s/n; printf "    --> Vref@27=%.4f V  span=%.2f mV  TC=%.1f ppm/C (-40..125)\n",
     v27,(mx-mn)*1000,(mx-mn)/(avg*165)*1e6}'

echo "==> Startup"
ngspice -b tb_startup.spice 2>&1 | awk '/^STARTUP/ {print "    "$0}'

echo "==> Line regulation"
ngspice -b tb_line.spice 2>&1 | awk '/^LINE/ {
  print "    Vref vs Vdd: "$0;
  split($2,a,"="); split($4,b,"=");           # 1.0 and 1.2
  split($5,c,"=");                              # 1.3
}'
