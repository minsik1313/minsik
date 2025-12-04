"""
P0-민무장: gdsfactory generic tech로 Current Mirror 직사각형 패턴을 찍어보는 제너레이터.

- D-A-B-A-B-D interdig 패턴을 유지한다.
- 지금은 MOS 없이 직사각형 shape만 배치한다.
- 나중에 sky130 MOS로 교체할 수 있게 helper 구조를 깔끔하게 둔다.
"""

import gdsfactory as gf

LAYER_DIFF = (1, 0)  # device rectangle layer (generic 가상 맵)
LAYER_LABEL = (10, 0)  # label 레이어 자리만 마련 (현재 미사용)


def make_current_mirror(
    cell_name: str = "cm_generic",
    nf_per_leg: int = 2,
    with_dummy: bool = True,
    pitch: float = 2.0,
    w: float = 1.0,
    h: float = 4.0,
):
    """
    Current Mirror interdig 패턴을 직사각형 레이어로 생성한다.

    패턴(왼→오): D_L - A1 - B1 - A2 - B2 - D_R
    (D = dummy, A = reference, B = output)

    nf_per_leg: A/B 각각이 가지는 직사각형 finger 개수.
    
    Origin은 왼쪽 dummy 근처(0, 0)로 시작해 오른쪽으로 배치한다.
    """

    component = gf.Component(cell_name)
    x_pos = 0.0

    base_rect = gf.components.rectangle(size=(w, h), layer=LAYER_DIFF)

    def add_strip(name_prefix: str, count: int, x_start: float):
        """name_prefix와 개수에 따라 직사각형 ref를 일렬 배치한다."""

        refs = []
        x_local = x_start
        for idx in range(count):
            ref = component << base_rect
            ref.move((x_local, 0))
            ref.name = f"{name_prefix}{idx}"
            refs.append(ref)
            x_local += w + pitch
        return refs, x_local

    d_left = a1 = b1 = a2 = b2 = d_right = []

    if with_dummy:
        d_left, x_pos = add_strip("D_L_", 1, x_pos)

    a1, x_pos = add_strip("A1_", nf_per_leg, x_pos)
    b1, x_pos = add_strip("B1_", nf_per_leg, x_pos)
    a2, x_pos = add_strip("A2_", nf_per_leg, x_pos)
    b2, x_pos = add_strip("B2_", nf_per_leg, x_pos)

    if with_dummy:
        d_right, x_pos = add_strip("D_R_", 1, x_pos)

    # TODO(v0.1): A/B source, gate, drain 라우팅/라벨 추가 시 LAYER_LABEL 활용
    # 반환값을 활용해 그룹별 배선/라벨을 붙일 수 있도록 리스트를 남긴다.
    _ = (d_left, a1, b1, a2, b2, d_right)
    return component


if __name__ == "__main__":
    component = make_current_mirror()
    component.write_gds("cm_generic.gds")
    print("Wrote cm_generic.gds")
