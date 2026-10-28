# haofu9003.github.io

Personal homepage of Hao Fu, built with Jekyll and served by GitHub Pages.

- `/` — academic homepage. Content (bio, news, publications, competitions) lives in `_config.yml` under `academic:`; layout in `_layouts/academic.html`.
- `/photography/` — photo gallery. Photo list and captions live in `_data/photos.yml`; layout in `_layouts/photography.html`.

## Adding a photo

1. Copy the original JPG to `photography/originals/<id>.jpg` (this folder is git-ignored).
2. Add an entry with the same `id` to `_data/photos.yml`.
3. Run `python3 scripts/build_photos.py` to generate `assets/photos/full/<id>.jpg` (3200px) and `assets/photos/thumb/<id>.jpg` (960px), then commit them.

## Local preview

```sh
bundle install
bundle exec jekyll serve
```
