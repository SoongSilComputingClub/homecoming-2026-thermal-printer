"""Render or print an SSCC Homecoming raffle ticket."""

import argparse
from dataclasses import dataclass
from pathlib import Path
import struct
import subprocess

WIDTH = 384
HEIGHT = 720
ART_HEIGHT = 376
FULL_CUT = b"\x1dV\x00"
FONT = "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf"
TIMETABLE_FONT = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


@dataclass(frozen=True)
class PrintOptions:
    fold_gap: int
    timetable_top: int
    timetable_bottom: int
    feed: int
    timetable_speed: int
    cut: bool


def render(number: int) -> bytes:
    code = str(number)
    artwork = f"""
        fill black font '{MONO}' font-size 27
        text 28,52 'SSCC HOMECOMING'
        font '{FONT}' font-size 29 text-anchor end
        text 691,52 '럭키드로우 추첨권'
        stroke black stroke-width 3 line 28,78 691,78
        stroke none text-anchor middle
        font '{MONO}' font-size 256
        text 360,281 '{code}'
        font '{FONT}' font-size 30
        text 360,334 '번호가 불리면 이 표를 보여주세요'
    """
    return render_panel(artwork)


def render_timetable(options: PrintOptions, qr_dot: int) -> bytes:
    # Published at https://homecoming-2026.sscc-ssu.com/
    schedule = (
        ("17:30", "사전 입장 및 안내"),
        ("18:00", "SSCC 연간 활동 소개"),
        ("18:30", "프로젝트 발표 및 시연"),
        ("19:30", "선후배 기술·진로 교류"),
        ("20:30", "럭키드로우"),
    )
    rows = []
    for index, (time, title) in enumerate(schedule):
        baseline = 144 + index * 116
        rows.append(f"""
            fill black stroke none font '{MONO}' font-size 42
            text 16,{baseline} '{time}'
            font '{TIMETABLE_FONT}' font-size 33 stroke black stroke-width 1
            text 16,{baseline + 43} '{title}'
        """)
        if index < len(schedule) - 1:
            rows.append(f"stroke black stroke-width 2 line 16,{baseline + 66} 367,{baseline + 66}")

    artwork = f"""
        translate 0,{options.timetable_top}
        fill black stroke none
        font '{TIMETABLE_FONT}' font-size 34
        text 24,53 '행사 시간표'
        font '{MONO}' font-size 23 text-anchor end
        text 358,52 '11.07'
        text-anchor start
        stroke black stroke-width 3 line 16,72 367,72
        {''.join(rows)}
        {homepage_qr_artwork(qr_dot)}
    """
    return render_panel(artwork, portrait_height=HEIGHT + options.timetable_top + options.timetable_bottom)


def homepage_qr_artwork(dot: int) -> str:
    modules = Path(__file__).with_name("homepage-qr.txt").read_text().splitlines()
    quiet = 4 * dot
    size = len(modules) * dot + 2 * quiet
    left, top = WIDTH - size, HEIGHT - size
    artwork = [f"fill white stroke none rectangle {left},{top} {WIDTH - 1},{HEIGHT - 1}",
               "fill black"]
    for row, cells in enumerate(modules):
        for column, cell in enumerate(cells):
            if cell == "1":
                x = left + quiet + column * dot
                y = top + quiet + row * dot
                artwork.append(f"rectangle {x},{y} {x + dot - 1},{y + dot - 1}")
    return "\n".join(artwork)


def render_panel(artwork: str, *, portrait_height: int | None = None) -> bytes:
    canvas = f"{WIDTH}x{portrait_height}" if portrait_height is not None else f"{HEIGHT}x{ART_HEIGHT}"
    orientation = [] if portrait_height is not None else [
        "-rotate", "90", "-gravity", "west", "-background", "white",
        "-extent", f"{WIDTH}x{HEIGHT}",
    ]
    return subprocess.run(
        ["convert", "-size", canvas, "xc:white", "-draw", artwork,
         *orientation, "-threshold", "50%", "pbm:-"],
        stdout=subprocess.PIPE,
        check=True,
    ).stdout


def render_fold_guide(gap: int) -> bytes:
    middle = gap // 2
    return subprocess.run(
        ["convert", "-size", f"{WIDTH}x{gap}", "xc:white",
         "-draw", f"stroke black stroke-width 2 stroke-dasharray 7,6 line 4,{middle} {WIDTH - 5},{middle}",
         "-threshold", "50%", "pbm:-"],
        stdout=subprocess.PIPE,
        check=True,
    ).stdout


def raster_panel(bitmap: bytes) -> bytes:
    magic, size, pixels = bitmap.split(b"\n", 2)
    width, height = map(int, size.split())
    row_bytes = WIDTH // 8
    if magic != b"P4" or width != WIDTH or not 1 <= height <= 65535:
        raise ValueError("Unexpected ticket bitmap format")
    if len(pixels) != row_bytes * height:
        raise ValueError("Unexpected ticket bitmap length")

    return b"\x1dv0\x00" + struct.pack("<HH", row_bytes, height) + pixels


def ticket_payload(front: bytes, back: bytes, options: PrintOptions) -> bytes:
    feed = b"\x1bJ" + bytes([options.feed]) if options.feed else b""
    payload = b"\x1b@\x1ba\x01"
    if back:
        payload += feed
    payload += raster_panel(front) + back + feed
    if options.cut:
        payload += FULL_CUT
    return payload


def speed_command(level: int) -> bytes:
    return b"\x1d(K\x02\x00\x32" + bytes([level])


def bounded_int(minimum: int, maximum: int):
    def parse(value: str) -> int:
        number = int(value)
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError(f"expected {minimum}–{maximum}")
        return number

    return parse


def number_range(value: str) -> range:
    try:
        first, last = map(int, value.split("-"))
        if 0 <= first <= last <= 99:
            return range(first, last + 1)
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("expected an ascending inclusive range, e.g. 0-60")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    numbers = parser.add_mutually_exclusive_group(required=True)
    numbers.add_argument("--num", type=bounded_int(0, 99), help="print one number (0–99)")
    numbers.add_argument("--range", dest="number_range", type=number_range, metavar="FIRST-LAST",
                         help="print each number once, including both endpoints")
    parser.add_argument("--printer", default="Receipt_Printer", help="CUPS queue name")
    parser.add_argument("--preview", type=Path, metavar="PNG", help="render a single ticket without printing")
    parser.add_argument("--no-timetable", action="store_true", help="omit the timetable and fold guide")
    parser.add_argument("--no-cut", action="store_true", help="disable automatic cutting")
    parser.add_argument("--feed", type=bounded_int(0, 255), default=48, help="paper feed in dots")
    parser.add_argument("--fold-gap", type=bounded_int(4, 255), default=24, help="fold gap in dots")
    parser.add_argument("--timetable-top", type=bounded_int(0, 255), default=40, help="top margin in dots")
    parser.add_argument("--timetable-bottom", type=bounded_int(0, 255), default=64, help="bottom margin in dots")
    parser.add_argument("--timetable-speed", type=bounded_int(0, 9), default=1,
                        help="ESC/POS speed level; 0 leaves the printer default")
    parser.add_argument("--qr-dot", type=bounded_int(2, 4), default=4, help="dots per QR module")
    args = parser.parse_args()
    if args.preview and args.num is None:
        parser.error("--preview requires --num")
    options = PrintOptions(args.fold_gap, args.timetable_top, args.timetable_bottom,
                           args.feed, args.timetable_speed, not args.no_cut)

    try:
        back_panels = [] if args.no_timetable else [
            render_fold_guide(options.fold_gap), render_timetable(options, args.qr_dot),
        ]
        if args.preview:
            orientation = ["-append"] if back_panels else [
                "-rotate", "-90", "-crop",
                f"{HEIGHT}x{ART_HEIGHT}+0+{WIDTH - ART_HEIGHT}", "+repage",
            ]
            subprocess.run(
                ["convert", "pbm:-", *orientation, f"png:{args.preview}"],
                input=b"".join([render(args.num), *back_panels]),
                check=True,
            )
            return

        back = b""
        if back_panels:
            fold, timetable = map(raster_panel, back_panels)
            if options.timetable_speed:
                timetable = speed_command(options.timetable_speed) + timetable + speed_command(0)
            back = fold + timetable
        requested = args.number_range if args.num is None else [args.num]
        payload = b"".join(ticket_payload(render(number), back, options) for number in requested)
        subprocess.run(
            ["lp", "-d", args.printer, "-o", "raw", "-t", "SSCC Homecoming raffle tickets"],
            input=payload,
            check=True,
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Ticket failed: {error}\n")


if __name__ == "__main__":
    main()
