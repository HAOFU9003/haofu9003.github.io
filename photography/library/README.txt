Photography library structure:

1) Main showcase photos
   photography/library/main/<your-image>.jpg
   photography/library/main/<your-image>.md        (optional sidecar metadata)
   or
   photography/library/main/_meta/<your-image>.md  (optional)

2) Theme photos
   photography/library/<theme-slug>/<your-image>.jpg
   photography/library/<theme-slug>/<your-image>.md
   or
   photography/library/<theme-slug>/_meta/<your-image>.md

3) Nested folders are supported
   photography/library/tokyo/shibuya/night01.jpg
   photography/library/tokyo/shibuya/_meta/night01.md

4) Sidecar md format
   ---
   title: Shibuya Crossing
   caption: Night street scene in Tokyo.
   ---

Run:
  python scripts/generate_photography_thumbs.py

This script creates:
  - thumbnails under sibling "_thumbs" folders
  - _data/photography_generated.json for Jekyll templates
