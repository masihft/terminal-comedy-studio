"""Look at the comedian before there is a stage to put it on.

    comedian-preview --list
    comedian-preview idle
    comedian-preview walk --strip
    comedian-preview --sheet assets/frames.svg
"""

from __future__ import annotations

import argparse
import sys
import time

from .character.frames import FRAMES
from .character.states import ANIMATIONS
from .ui.renderer import side_by_side, to_ansi, to_svg

HOME = "\x1b[2J\x1b[H"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="comedian-preview",
        description="Preview the Terminal Comedy Studio pixel comedian.",
    )
    parser.add_argument("animation", nargs="?", default="idle", help="animation to play")
    parser.add_argument("--list", action="store_true", help="list animations and frames")
    parser.add_argument("--strip", action="store_true", help="print the frames side by side")
    parser.add_argument("--sheet", metavar="FILE", help="write an SVG contact sheet and exit")
    parser.add_argument("--all", action="store_true", help="with --sheet: every frame")
    parser.add_argument("--plain", action="store_true", help="no ANSI colour")
    parser.add_argument("--frames", metavar="N", type=int, default=0, help="stop after N frames")
    return parser


def _listing() -> str:
    lines = ["animations"]
    for name, animation in sorted(ANIMATIONS.items()):
        kind = "loop" if animation.loop else "once"
        lines.append(f"  {name:<11} {animation.fps:>4} fps {kind:<4} {' '.join(animation.frames)}")
    lines.append("")
    lines.append(f"frames ({len(FRAMES)})")
    names = sorted(FRAMES)
    for i in range(0, len(names), 3):
        lines.append("  " + "  ".join(f"{n:<14}" for n in names[i:i + 3]).rstrip())
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.animation not in ANIMATIONS and not (args.list or args.all):
        known = ", ".join(sorted(ANIMATIONS))
        print(f"unknown animation '{args.animation}'. choose: {known}", file=sys.stderr)
        return 2

    if args.list:
        print(_listing())
        return 0

    if args.sheet:
        frames = (
            sorted(FRAMES.values(), key=lambda f: f.name)
            if args.all
            else [FRAMES[name] for name in ANIMATIONS[args.animation].frames]
        )
        with open(args.sheet, "w", encoding="utf-8") as handle:
            handle.write(to_svg(frames))
        print(f"{args.sheet}: {len(frames)} frames")
        return 0

    animation = ANIMATIONS[args.animation]
    frames = [FRAMES[name] for name in animation.frames]

    if args.strip:
        print(side_by_side(frames, colour=not args.plain))
        return 0

    if not sys.stdout.isatty():
        print(side_by_side(frames, colour=not args.plain))
        return 0

    index, elapsed, period, shown = 0, 0.0, 1.0 / animation.fps, 0
    try:
        while True:
            sys.stdout.write(HOME)
            sys.stdout.write(to_ansi(frames[index], colour=not args.plain))
            sys.stdout.write(f"\n\n {animation.name} · {animation.frames[index]} · {animation.fps:g} fps\n")
            sys.stdout.flush()
            shown += 1
            if args.frames and shown >= args.frames:
                break
            time.sleep(period)
            index = (index + 1) % len(frames)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
