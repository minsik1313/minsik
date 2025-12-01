"""테스트 드라이버: sky130 current mirror GDS를 pair 수(num_pairs) 스윕으로 생성합니다."""
from cm_sky130 import make_sky130_current_mirror


def main() -> None:
    configs = [
        {"cell_name": "cm_sky130_nf2", "num_pairs": 2},
        {"cell_name": "cm_sky130_nf4", "num_pairs": 4},
    ]

    for cfg in configs:
        component = make_sky130_current_mirror(
            cell_name=cfg["cell_name"],
            num_pairs=cfg["num_pairs"],
            with_dummy=True,
            w=1.0,
            l=0.15,
            sd_pitch_pair=2.0,
        )
        gds_name = f"{cfg['cell_name']}.gds"
        component.write_gds(gds_name)
        print(f"[P1] wrote {gds_name}")


if __name__ == "__main__":
    main()
