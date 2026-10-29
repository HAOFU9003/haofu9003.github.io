#!/usr/bin/env python3
"""Sync the photography gallery with the git-ignored originals folder.

    photography/originals/<id>.jpg  ->  assets/photos/full/<id>.jpg   (long edge 3200px)
                                    ->  assets/photos/thumb/<id>.jpg  (long edge 960px)
                                    ->  an entry in _data/photos.yml

The originals folder is the source of truth:
  * a new original gets compressed and appended to _data/photos.yml
    (title from the file name, date from EXIF, place looked up from the EXIF
    GPS position when the photo has one; fill in the rest yourself);
  * a deleted original has its entry and compressed files removed;
  * an entry with `hidden: true` stays in photos.yml but is not built or shown.

File names are normalised to lowercase-with-dashes ids, e.g.
"Austin Sunset.JPG" -> austin-sunset.jpg. Name files descriptively before
adding them so photos.yml stays easy to read.

Usage:
    python3 scripts/build_photos.py           # sync once
    python3 scripts/build_photos.py --watch   # keep syncing while you add photos
    python3 scripts/build_photos.py --force   # rebuild every compressed image
    python3 scripts/build_photos.py --no-geocode  # never send GPS positions online

Place names come from OpenStreetMap's Nominatim service: only the photo's
coordinates are sent, and only for newly added photos that carry GPS data.

Requires Pillow and PyYAML (pip install pillow pyyaml).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = ROOT / "photography" / "originals"
OUT = ROOT / "assets" / "photos"
DATA = ROOT / "_data" / "photos.yml"
DIMENSIONS = ROOT / "_data" / "photo_sizes.yml"  # generated: thumbnail size per photo

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
SIZES = {"full": (3200, 88), "thumb": (960, 82)}  # name -> (long edge, JPEG quality)

# EXIF orientation -> transpose ops. ImageOps.exif_transpose crashes on some
# camera EXIF blocks in older Pillow, so apply the rotation by hand.
ORIENTATION = {
    2: [Image.FLIP_LEFT_RIGHT], 3: [Image.ROTATE_180], 4: [Image.FLIP_TOP_BOTTOM],
    5: [Image.ROTATE_90, Image.FLIP_TOP_BOTTOM], 6: [Image.ROTATE_270],
    7: [Image.ROTATE_270, Image.FLIP_TOP_BOTTOM], 8: [Image.ROTATE_90],
}
EXIF_DATETIME_ORIGINAL, EXIF_DATETIME, EXIF_GPS = 0x9003, 0x0132, 0x8825
GEOCODE_URL = "https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=10&accept-language=en&lat={lat}&lon={lon}"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "photo"


def find_originals() -> dict[str, Path]:
    """Return {id: path}, renaming files to <slug>.jpg/.png where needed."""
    found: dict[str, Path] = {}
    for path in sorted(ORIGINALS.iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
            continue
        ext = ".png" if path.suffix.lower() == ".png" else ".jpg"
        pid = slugify(path.stem)
        target = path.with_name(pid + ext)
        if target != path:
            n = 2
            while target.exists() or pid in found:
                pid = f"{slugify(path.stem)}-{n}"
                target = path.with_name(pid + ext)
                n += 1
            path.rename(target)
            print(f"renamed  {path.name} -> {target.name}")
        found[pid] = target
    return found


def exif_date(path: Path) -> str | None:
    try:
        with Image.open(path) as im:
            exif = im._getexif() or {}
    except Exception:
        return None
    raw = exif.get(EXIF_DATETIME_ORIGINAL) or exif.get(EXIF_DATETIME)
    m = re.match(r"(\d{4}):(\d{2}):(\d{2})", str(raw or ""))
    return f"{m[1]}-{m[2]}-{m[3]}" if m else None


def exif_gps(path: Path) -> tuple[float, float] | None:
    """Return (lat, lon) from EXIF, or None. Many cameras write an empty GPS block."""
    try:
        with Image.open(path) as im:
            gps = (im._getexif() or {}).get(EXIF_GPS) or {}
        def degrees(dms) -> float:
            # Older Pillow gives (numerator, denominator) tuples, newer gives rationals.
            d, m, sec = (v[0] / v[1] if isinstance(v, tuple) else float(v) for v in dms)
            return d + m / 60 + sec / 3600
        lat, lon = degrees(gps[2]), degrees(gps[4])
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OSError):
        return None
    if gps.get(1) == "S":
        lat = -lat
    if gps.get(3) == "W":
        lon = -lon
    return lat, lon


def place_name(lat: float, lon: float) -> str | None:
    """Reverse-geocode to "City, Country" via OpenStreetMap Nominatim."""
    req = urllib.request.Request(GEOCODE_URL.format(lat=lat, lon=lon),
                                 headers={"User-Agent": "haofu9003.github.io photo script"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            addr = json.load(resp).get("address", {})
    except Exception as exc:
        print(f"warning: place lookup failed ({exc})", file=sys.stderr)
        return None
    finally:
        time.sleep(1)  # Nominatim allows at most one request per second
    local = next((addr[k] for k in ("city", "town", "village", "municipality", "county", "state") if k in addr), None)
    parts = [p for p in (local, addr.get("country")) if p]
    return ", ".join(parts) or None


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


def split_entries(text: str) -> tuple[str, list[str]]:
    """Split photos.yml into its header comment and one text block per entry,
    so entries can be added/removed without reformatting the rest of the file."""
    parts = re.split(r"(?m)^(?=- id:)", text)
    return parts[0], parts[1:]


def entry_id(block: str) -> str:
    return str(yaml.safe_load(block)[0]["id"])


def new_entry(pid: str, src: Path, geocode: bool) -> str:
    title = pid.replace("-", " ").title()
    gps = exif_gps(src) if geocode else None
    place = place_name(*gps) if gps else None
    lines = [f'- id: "{pid}"', f"  title: {title}"]
    if place:
        lines.append(f'  place: "{place}"  # from GPS; check / add a caption')
    else:
        lines.append('  place: ""  # TODO: fill in place / caption')
    date = exif_date(src)
    if date:
        lines.append(f"  date: {date}")
    return "\n".join(lines) + "\n\n"


def sync(force: bool = False, geocode: bool = True) -> None:
    originals = find_originals()
    header, blocks = split_entries(DATA.read_text(encoding="utf-8"))
    listed = {entry_id(b): b for b in blocks}

    # Drop entries whose original was deleted. Skip this when the folder is
    # empty (e.g. a fresh clone without originals) so nothing is wiped by accident.
    gone = [pid for pid in listed if pid not in originals]
    if gone and originals:
        blocks = [b for b in blocks if entry_id(b) not in gone]
        for pid in gone:
            print(f"removed  {pid} (original deleted)")
    elif gone:
        print(f"warning: {ORIGINALS.relative_to(ROOT)}/ has no photos; not removing anything", file=sys.stderr)

    added = [pid for pid in originals if pid not in listed]
    if blocks and not blocks[-1].endswith("\n\n"):
        blocks[-1] = blocks[-1].rstrip("\n") + "\n\n"
    for pid in added:
        blocks.append(new_entry(pid, originals[pid], geocode))
        print(f"added    {pid} -> _data/photos.yml")

    if (gone and originals) or added:
        DATA.write_text(header + "".join(blocks).rstrip("\n") + "\n", encoding="utf-8")

    entries = yaml.safe_load(DATA.read_text(encoding="utf-8")) or []
    visible = {str(e["id"]) for e in entries if not e.get("hidden")}

    for pid in sorted(visible & originals.keys()):
        src = originals[pid]
        for name, (edge, quality) in SIZES.items():
            dst = OUT / name / f"{pid}.jpg"
            if not force and dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
                continue
            build(src, dst, edge, quality)
            print(f"built    {name:5s} {pid}  {dst.stat().st_size / 1e6:.2f} MB")

    # Remove compressed files that are no longer shown (deleted or hidden).
    for name in SIZES:
        for f in (OUT / name).glob("*.jpg"):
            if f.stem not in visible:
                f.unlink()
                print(f"deleted  {f.relative_to(ROOT)}")

    write_dimensions(visible)


def write_dimensions(visible: set[str]) -> None:
    """Record each thumbnail's pixel size so the gallery can lay out rows by aspect ratio."""
    lines = ["# Generated by scripts/build_photos.py; do not edit.",
             "# Thumbnail [width, height] per photo id, used for the gallery row layout."]
    for pid in sorted(visible):
        thumb = OUT / "thumb" / f"{pid}.jpg"
        if thumb.exists():
            with Image.open(thumb) as im:
                lines.append(f'"{pid}": [{im.width}, {im.height}]')
    text = "\n".join(lines) + "\n"
    if not DIMENSIONS.exists() or DIMENSIONS.read_text(encoding="utf-8") != text:
        DIMENSIONS.write_text(text, encoding="utf-8")
        print(f"updated  {DIMENSIONS.relative_to(ROOT)}")


def snapshot() -> dict[str, float]:
    return {p.name: p.stat().st_mtime for p in ORIGINALS.iterdir() if p.is_file()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="rebuild even if outputs are up to date")
    parser.add_argument("--watch", action="store_true", help="keep running and sync whenever originals change")
    parser.add_argument("--no-geocode", action="store_true", help="do not look up place names from GPS")
    args = parser.parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # show progress immediately in --watch mode

    ORIGINALS.mkdir(parents=True, exist_ok=True)
    sync(args.force, not args.no_geocode)
    if not args.watch:
        return 0

    print(f"watching {ORIGINALS.relative_to(ROOT)}/ for changes (Ctrl+C to stop)")
    last = snapshot()
    try:
        while True:
            time.sleep(2)
            current = snapshot()
            if current != last:
                time.sleep(2)  # let large copies finish
                sync(geocode=not args.no_geocode)
                last = snapshot()
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
