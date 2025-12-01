"""테스트 드라이버: current mirror 패턴 GDS를 여러 설정으로 생성한다."""
from cm_generator import make_current_mirror


def main():
    configs = [
        {"cell_name": "cm_nf2", "nf_per_leg": 2},
        {"cell_name": "cm_nf4", "nf_per_leg": 4},
    ]

    for cfg in configs:
        component = make_current_mirror(
            cell_name=cfg["cell_name"],
            nf_per_leg=cfg["nf_per_leg"],
            with_dummy=True,
            pitch=2.0,
            w=1.0,
            h=4.0,
        )
        gds_name = f"{cfg['cell_name']}.gds"
        component.write_gds(gds_name)
        print(f"[P0] wrote {gds_name}")


if __name__ == "__main__":
    main()
