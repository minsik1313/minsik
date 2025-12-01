from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_PATHS = [
    Path("p0_current_mirror/README_min_env.md"),
    Path("p0_current_mirror/env/install_min_env.sh"),
    Path("p0_current_mirror/src/cm_generator.py"),
    Path("p0_current_mirror/src/run_generator.py"),
    Path("p1_sky130_current_mirror/README_sky130.md"),
    Path("p1_sky130_current_mirror/env/install_sky130_env.sh"),
    Path("p1_sky130_current_mirror/src/cm_sky130.py"),
    Path("p1_sky130_current_mirror/src/run_cm_sky130.py"),
]

LANG_BY_SUFFIX = {
    ".md": "markdown",
    ".py": "python",
    ".sh": "bash",
}


def format_block(path: Path) -> str:
    suffix = path.suffix
    language = LANG_BY_SUFFIX.get(suffix, "")
    content = path.read_text(encoding="utf-8")
    header = f"===== FILE: {path.as_posix()} ====="
    fenced = f"```{language}\n{content}\n```" if language else content
    return f"{header}\n{fenced}\n"


def normalize_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    if path.exists():
        return path
    candidate = ROOT_DIR / path
    return candidate


def build_payload(paths: Iterable[Path]) -> str:
    lines: list[str] = []
    for p in paths:
        resolved = normalize_path(p)
        lines.append(format_block(resolved))
    return "\n".join(lines).rstrip() + "\n"


def build_relay_header(
    recipient: str,
    sender: str,
    via: str | None,
    summary_lines: list[str],
) -> str:
    header = f"📨 to {recipient} (from {sender}"
    if via:
        header += f", via {via}"
    header += ")"

    lines = [header, ""]

    if summary_lines:
        lines.append("[업데이트 요약]")
        lines.extend(summary_lines)
        lines.append("")

    lines.append("[export_for_gpt.py 출력]")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="선택한 파일을 GPT로 바로 복붙할 수 있는 형식으로 묶어 출력합니다.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="저장할 파일 경로. 지정하지 않으면 표준 출력으로 작성합니다.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=None,
        help="묶어 보낼 파일 경로 목록 (생략 시 기본 리스트 사용)",
    )
    parser.add_argument(
        "--recipient",
        default="지피티",
        help="상대 에이전트 이름. 기본값: 지피티",
    )
    parser.add_argument(
        "--sender",
        default="코덱이",
        help="보내는 사람 이름. 기본값: 코덱이",
    )
    parser.add_argument(
        "--via",
        default="민식",
        help="중계자 이름. 빈 문자열로 두면 via 구문을 생략합니다.",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="to/from 머리말을 제외하고 파일 내용만 출력합니다.",
    )
    parser.add_argument(
        "--summary",
        action="append",
        default=[],
        help="업데이트 요약을 한 줄씩 추가합니다. 여러 번 지정 가능합니다.",
    )
    parser.add_argument(
        "--show-defaults",
        action="store_true",
        help="기본으로 묶이는 파일 경로만 출력하고 종료합니다.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.show_defaults:
        for p in DEFAULT_PATHS:
            print(p.as_posix())
        return

    target_paths = args.paths if args.paths else DEFAULT_PATHS
    payload = build_payload(target_paths)

    header = ""
    if not args.no_header:
        via = args.via or None
        header = build_relay_header(args.recipient, args.sender, via, args.summary)
        payload = f"{header}\n{payload}"

    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
