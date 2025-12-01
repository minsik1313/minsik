"""
P1-sky130: sky130 PCell로 D_L–(A0,B0…A{num_pairs-1},B{num_pairs-1})–D_R current mirror 패턴을 생성합니다.

- Strict hierarchy: 디바이스 생성 → 페어 배치 → 전체 current mirror 조립.
- Smart relative placement: 이전 소자 bbox 기반 이동으로 W/L 변화에도 패턴 유지.
- Pair-first: A/B 페어 리스트를 보존해 소스 공유·라벨·라우팅 헬퍼에 재활용.
- Guard-ring hook: 이후 단계에서 ring을 추가할 수 있도록 인터페이스만 미리 확보.
"""

from __future__ import annotations

import gdsfactory as gf
import sky130

# Sky130 DRC 방어용 최소 여유 상수 (설계 지침)
MIN_LI1_SPACING = 0.2  # um, li1 간 최소 간격 여유
MIN_DIFF_SPACING = 0.3  # um, diffusion 간 최소 간격 권장
GATE_EXTENSION = 0.13  # um, poly 양쪽 익스텐션 권장치 (참고용)

LAYER_MAP = {
    "label": (10, 0),  # 시각용 라벨 레이어(가상)
    "source_metal": (2, 0),  # 공통 소스 레일 스케치용 가상 레이어
    "tap_ring": (3, 0),  # 가드/탭 링 스케치용 가상 레이어
}


def add_poly_to_m1_contact(*_args, **_kwargs) -> None:
    """Poly → Licon → li1 → Mcon → Metal1 스택을 위한 헬퍼 (TODO 구현)."""

    return None


def add_diff_to_m1_contact(*_args, **_kwargs) -> None:
    """Diff → Licon → li1 → Mcon → Metal1 스택을 위한 헬퍼 (TODO 구현)."""

    return None


def _make_nmos_device(
    component: gf.Component,
    name_prefix: str,
    index: int,
    w: float,
    l: float,
) -> gf.ComponentReference:
    """Sky130 nMOS PCell 하나를 생성해 component에 추가하고 ref를 반환합니다."""

    device = sky130.components.nmos(
        w=w,
        l=l,
    )
    ref = component << device
    ref.name = f"{name_prefix}{index}"
    return ref


def _add_dummy(
    component: gf.Component,
    name_prefix: str,
    x_start: float,
    w: float,
    l: float,
    sd_pitch: float,
) -> tuple[list[gf.ComponentReference], float]:
    """더미 디바이스 하나를 배치하고 다음 시작점을 반환합니다."""

    dummy_ref = _make_nmos_device(component, name_prefix, 0, w=w, l=l)
    dummy_ref.move((x_start, 0.0))
    spacing = max(sd_pitch, MIN_DIFF_SPACING, MIN_LI1_SPACING)
    next_x_start = dummy_ref.bbox.xmax + spacing
    return [dummy_ref], next_x_start


def _add_pair(
    component: gf.Component,
    pair_index: int,
    x_start: float,
    w: float,
    l: float,
    sd_pitch_pair: float,
) -> tuple[tuple[gf.ComponentReference, gf.ComponentReference], float]:
    """A/B 한 쌍을 소스 공유 형태로 배치하고 다음 시작점을 반환합니다."""

    ref_a = _make_nmos_device(component, "A_", pair_index, w=w, l=l)
    ref_b = _make_nmos_device(component, "B_", pair_index, w=w, l=l)

    # A 위치 기준 배치
    ref_a.move((x_start, 0.0))

    # B를 A와 소스가 맞닿도록 오른쪽으로 이동 (bbox 기준 접촉)
    dx = ref_a.bbox.xmax - ref_b.bbox.xmin
    ref_b.movex(dx)

    spacing = max(sd_pitch_pair, MIN_DIFF_SPACING, MIN_LI1_SPACING)
    next_x_start = ref_b.bbox.xmax + spacing
    return (ref_a, ref_b), next_x_start


def _label_group(component: gf.Component, refs: list[gf.ComponentReference], text: str) -> None:
    """그룹 중앙 근처에 라벨을 찍는다."""

    if not refs:
        return

    center_ref = refs[len(refs) // 2]
    x_coord, y_coord = center_ref.center
    component.add_label(
        text=text,
        position=(x_coord, y_coord),
        layer=LAYER_MAP["label"],
    )


def _pair_groups(
    ref_pairs: list[tuple[gf.ComponentReference, gf.ComponentReference]]
) -> tuple[list[gf.ComponentReference], list[gf.ComponentReference]]:
    """페어 리스트에서 A/B 리스트를 추출한다."""

    a_list = [a for a, _ in ref_pairs]
    b_list = [b for _, b in ref_pairs]
    return a_list, b_list


def route_common_source(
    component: gf.Component,
    ref_pairs: list[tuple[gf.ComponentReference, gf.ComponentReference]],
    thickness: float = 0.5,
    margin: float = MIN_LI1_SPACING,
) -> None:
    """페어 전체 bbox 기준으로 공통 소스 레일을 추가한다."""

    if not ref_pairs:
        return

    x_min = min(ref_a.bbox.xmin for ref_a, _ in ref_pairs)
    x_max = max(ref_b.bbox.xmax for _, ref_b in ref_pairs)
    y_min = min(min(ref_a.bbox.ymin, ref_b.bbox.ymin) for ref_a, ref_b in ref_pairs)

    rail = [
        (x_min - margin, y_min - thickness),
        (x_max + margin, y_min - thickness),
        (x_max + margin, y_min + thickness),
        (x_min - margin, y_min + thickness),
    ]
    component.add_polygon(rail, layer=LAYER_MAP["source_metal"])


def add_guard_ring(component: gf.Component, refs: list[gf.ComponentReference], margin: float = 5.0) -> None:
    """Latch-up 방지를 위한 tap/guard ring 스케치.

    - 실제 tap/컨택 세부 규칙은 후속 단계에서 보완합니다.
    - 현재는 사각 프레임을 네 개의 직사각형으로 둘러 배치합니다.
    """

    if not refs:
        return

    x_min = min(r.bbox.xmin for r in refs)
    x_max = max(r.bbox.xmax for r in refs)
    y_min = min(r.bbox.ymin for r in refs)
    y_max = max(r.bbox.ymax for r in refs)

    outer_min_x = x_min - margin
    outer_max_x = x_max + margin
    outer_min_y = y_min - margin
    outer_max_y = y_max + margin

    ring_width = max(0.5, margin * 0.1)  # 기본 두께를 margin의 10% 이상 0.5um로 유지
    inner_min_x = outer_min_x + ring_width
    inner_max_x = outer_max_x - ring_width
    inner_min_y = outer_min_y + ring_width
    inner_max_y = outer_max_y - ring_width

    # frame을 네 개의 직사각형으로 추가
    rectangles = [
        # Bottom
        [(outer_min_x, outer_min_y), (outer_max_x, outer_min_y + ring_width)],
        # Top
        [(outer_min_x, outer_max_y - ring_width), (outer_max_x, outer_max_y)],
        # Left
        [(outer_min_x, outer_min_y), (outer_min_x + ring_width, outer_max_y)],
        # Right
        [(outer_max_x - ring_width, outer_min_y), (outer_max_x, outer_max_y)],
    ]

    for (x0, y0), (x1, y1) in rectangles:
        component.add_polygon(
            [
                (x0, y0),
                (x1, y0),
                (x1, y1),
                (x0, y1),
            ],
            layer=LAYER_MAP["tap_ring"],
        )

    component.info["guard_ring"] = {
        "outer_bbox": (outer_min_x, outer_min_y, outer_max_x, outer_max_y),
        "inner_bbox": (inner_min_x, inner_min_y, inner_max_x, inner_max_y),
        "ring_width": ring_width,
    }


def make_sky130_current_mirror(
    cell_name: str = "cm_sky130_nf2",
    num_pairs: int = 2,
    with_dummy: bool = True,
    w: float = 1.0,  # (um) device width
    l: float = 0.15,  # (um) channel length
    sd_pitch_pair: float = 2.0,  # (um) A/B 소스 공유 페어 간격(MIN_DIFF_SPACING 이상)
    gate_dir: str = "vertical",  # 게이트 방향 힌트(현재 미사용)
) -> gf.Component:
    """
    Sky130 nMOS current mirror를 D_L–(A0,B0 … A{num_pairs-1},B{num_pairs-1})–D_R 패턴으로 배치합니다.

    - A/B를 **pair** 단위로 묶어 소스 공유 배치를 적용합니다.
    - bbox 기반 상대 좌표로 W/L 변경 시에도 인터디직 패턴을 유지합니다.
    - pair/A/B 리스트를 info에 저장해 후속 라우팅/라벨링 단계에서 재사용합니다.
    """

    if num_pairs <= 0:
        raise ValueError("num_pairs must be a positive integer")

    component = gf.Component(cell_name)

    d_left: list[gf.ComponentReference] = []
    d_right: list[gf.ComponentReference] = []
    pairs: list[tuple[gf.ComponentReference, gf.ComponentReference]] = []

    x_pos = 0.0

    if with_dummy:
        d_left, x_pos = _add_dummy(
            component, "D_L_", x_pos, w=w, l=l, sd_pitch=sd_pitch_pair
        )

    for pair_idx in range(num_pairs):
        pair, x_pos = _add_pair(
            component,
            pair_idx,
            x_pos,
            w=w,
            l=l,
            sd_pitch_pair=sd_pitch_pair,
        )
        pairs.append(pair)

    if with_dummy:
        d_right, x_pos = _add_dummy(
            component, "D_R_", x_pos, w=w, l=l, sd_pitch=sd_pitch_pair
        )

    a_list, b_list = _pair_groups(pairs)

    _label_group(component, a_list, "REF_D")
    _label_group(component, b_list, "OUT_D")
    _label_group(component, a_list + b_list, "GATE_BIAS")
    _label_group(component, a_list + b_list, "VSS")

    route_common_source(component, pairs)
    add_guard_ring(component, refs=[*d_left, *d_right, *a_list, *b_list])

    component.info.update(
        {
            "dummies": {"left": d_left, "right": d_right},
            "pairs": pairs,
            "a_list": a_list,
            "b_list": b_list,
        }
    )

    return component


if __name__ == "__main__":
    cmp = make_sky130_current_mirror()
    cmp.write_gds("cm_sky130_nf2.gds")
    print("Wrote cm_sky130_nf2.gds")
