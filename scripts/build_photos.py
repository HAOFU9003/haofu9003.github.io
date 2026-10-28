#!/usr/bin/env python3
"""Build web-sized photos for /photography/ from the git-ignored originals.

    photography/originals/<id>.jpg  ->  assets/photos/full/<id>.jpg   (long edge 3200px)
                                    ->  assets/photos/thumb/<id>.jpg  (long edge 960px)

Only ids listed in _data/photos.yml are built. Existing outputs that are newer
than their original are skipped; pass --force to rebuild everything.
Requires Pillow (pip install pillow) and PyYAML.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = ROOT / "photography" / "originals"
OUT = ROOT / "assets" / "photos"
DATA = ROOT / "_data" / "photos.yml"

SIZES = {"full": (3200, 88), "thumb": (960, 82)}  # name -> (long edge, JPEG quality)

# EXIF orientation -> transpose ops. ImageOps.exif_transpose crashes on some
# camera EXIF blocks in older Pillow, so apply the rotation by hand.
ORIENTATION = {
    2: [Image.FLIP_LEFT_RIGHT], 3: [Image.ROTATE_180], 4: [Image.FLIP_TOP_BOTTOM],
    5: [Image.ROTATE_90, Image.FLIP_TOP_BOTTOM], 6: [Image.ROTATE_270],
    7: [Image.ROTATE_270, Image.FLIP_TOP_BOTTOM], 8: [Image.ROTATE_90],
}


def build(src: Path, dst: Path, long_edge: int, quality: int) -> None:
    with Image.open(src) as im:
        icc = im.info.get("icc_profile")
        ops = ORIENTATION.get(im.getexif().get(0x0112), [])
        im = im.convert("RGB")
        for op in ops:
            im = im.transpose(op)
        im.thumbnail((long_edge, long_edge), Image.LANCZOS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        im.save(dst, "JPEG", quality=quality, optimize=True, progressive=True, icc_profile=icc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="rebuild even if outputs are up to date")
    args = parser.parse_args()

    ids = [str(p["id"]) for p in yaml.safe_load(DATA.read_text(encoding="utf-8"))]
    missing = []
    for pid in ids:
        src = ORIGINALS / f"{pid}.jpg"
        if not src.exists():
            missing.append(pid)
            continue
        for name, (edge, quality) in SIZES.items():
            dst = OUT / name / f"{pid}.jpg"
            if not args.force and dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
                continue
            build(src, dst, edge, quality)
            print(f"{name:5s} {pid}  {dst.stat().st_size / 1e6:.2f} MB")

    # Remove outputs for photos no longer listed in photos.yml.
    for name in SIZES:
        for f in (OUT / name).glob("*.jpg"):
            if f.stem not in ids:
                f.unlink()
                print(f"removed {f.relative_to(ROOT)}")

    if missing:
        print(f"warning: no original found for {', '.join(missing)} in {ORIGINALS.relative_to(ROOT)}/", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
