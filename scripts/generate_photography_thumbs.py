#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Pillow is required. Install it with: pip install pillow"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
LIBRARY_ROOT = ROOT / "photography" / "library"
DATA_FILE = ROOT / "_data" / "photography_generated.json"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def parse_front_matter(md_path: Path) -> dict[str, str]:
    if not md_path.exists():
        return {}

    text = md_path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---"):
        return {"caption": text.strip()}

    lines = text.splitlines()
    if len(lines) < 3:
        return {}

    meta: dict[str, str] = {}
    key: str | None = None
    body_start = 0
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body_start = i + 1
            break
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            key = k.strip()
            meta[key] = v.strip().strip('"').strip("'")
        elif key is not None and line.startswith((" ", "\t")):
            meta[key] = (meta[key] + "\n" + line.strip()).strip()

    if "caption" not in meta:
        body = "\n".join(lines[body_start:]).strip()
        if body:
            meta["caption"] = body
    return meta


def sidecar_for(image_path: Path) -> Path | None:
    same_folder = image_path.with_suffix(".md")
    if same_folder.exists():
        return same_folder
    meta_folder = image_path.parent / "_meta" / f"{image_path.stem}.md"
    if meta_folder.exists():
        return meta_folder
    return None


def make_thumb(src: Path, dest: Path, max_size: int, quality: int, force: bool) -> bool:
    if dest.exists() and not force and dest.stat().st_mtime >= src.stat().st_mtime:
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert("RGB")
        im.thumbnail((max_size, max_size))
        im.save(dest, format="JPEG", optimize=True, quality=quality)
    return True


def collect_images(theme_dir: Path) -> list[Path]:
    images: list[Path] = []
    for path in sorted(theme_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in IMAGE_EXTS:
            continue
        if "_thumbs" in path.parts:
            continue
        images.append(path)
    return images


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate missing photography thumbnails and data index."
    )
    parser.add_argument("--force", action="store_true", help="Regenerate all thumbnails.")
    parser.add_argument("--max-size", type=int, default=1200, help="Max width/height of thumbnail.")
    parser.add_argument("--quality", type=int, default=82, help="JPEG quality (1-95).")
    args = parser.parse_args()

    LIBRARY_ROOT.mkdir(parents=True, exist_ok=True)
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    photos: list[dict[str, str]] = []
    updated = 0
    themes: dict[str, int] = {}

    for theme_dir in sorted([p for p in LIBRARY_ROOT.iterdir() if p.is_dir()]):
        theme = theme_dir.name
        themes.setdefault(theme, 0)
        for image in collect_images(theme_dir):
            rel = image.relative_to(ROOT)
            thumb = image.parent / "_thumbs" / f"{image.stem}.jpg"
            if make_thumb(image, thumb, args.max_size, args.quality, args.force):
                updated += 1

            sidecar = sidecar_for(image)
            meta = parse_front_matter(sidecar) if sidecar else {}
            title = meta.get("title", re.sub(r"[_-]+", " ", image.stem).strip())
            caption = meta.get("caption", "")

            photos.append(
                {
                    "theme": theme,
                    "title": title,
                    "caption": caption,
                    "full_url": "/" + rel.as_posix(),
                    "thumb_url": "/" + thumb.relative_to(ROOT).as_posix(),
                }
            )
            themes[theme] += 1

    payload = {
        "photos": photos,
        "themes": [{"slug": k, "count": v} for k, v in sorted(themes.items())],
    }
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Generated index with {len(photos)} photos.")
    print(f"Updated {updated} thumbnail(s).")
    print(f"Data file: {DATA_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
