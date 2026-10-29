# haofu9003.github.io

Source of [haofu9003.github.io](https://haofu9003.github.io), Hao Fu's personal site. It is a plain Jekyll site that GitHub Pages builds and serves.

| Page | URL | Content | Layout |
| --- | --- | --- | --- |
| Academic homepage | `/` | `_config.yml` → `academic:` | `_layouts/academic.html` |
| Photography | `/photography/` | `_data/photos.yml` | `_layouts/photography.html` |

## Layout

```
_config.yml              site settings + all academic page text
_data/photos.yml         photo list (title, place, date, caption)
_data/photo_sizes.yml    thumbnail sizes for the row layout — generated, do not edit
_layouts/                academic.html, photography.html
_includes/               shared head, nav and footer
assets/css/              academic.css (shared styles, dark mode), photography.css
assets/js/               site.js (nav, theme toggle), photography.js (gallery, lightbox)
assets/img/              avatar; papers/ = one figure per publication; logos/ = lab badges
assets/photos/           compressed photos: full/ (3200px) and thumb/ (960px)
photography/originals/   original photos — git-ignored, local only
scripts/build_photos.py  syncs originals → compressed photos + photos.yml
```

## Editing the academic page

Everything on `/` is in `_config.yml` under `academic:`: name, bio (HTML allowed), links, research interests, news, publications and competitions. Leave a field as `""` to hide it.

A publication entry:

```yaml
- title: "Paper title"
  authors: "A, <strong>Hao Fu</strong>, B"     # optional
  venue: "Conference name"
  year: 2027
  pdf: "assets/papers/my-paper.pdf"           # local file or URL
  image: "assets/img/papers/my-paper.jpg"     # representative figure, ~16:10
  arxiv: "https://arxiv.org/abs/..."          # optional
  project: "https://..."                      # optional project website
```

Competitions take `title`, `role`, `description` and an optional `website`.

## Managing photos

`photography/originals/` is the source of truth. Only the compressed copies are committed, so keep your own backup of the originals.

```sh
python3 scripts/build_photos.py            # sync once
python3 scripts/build_photos.py --watch    # keep syncing while you add photos
python3 scripts/build_photos.py --force    # rebuild every compressed image
```

- **Add**: put the original in `photography/originals/` with a descriptive name (e.g. `austin-sunset.jpg`; names are normalised to lowercase-with-dashes) and run the script. It writes the full and thumbnail versions and appends an entry to `_data/photos.yml` with the date from EXIF and, if the photo has GPS data, the place (e.g. "Kangding, China"). Then check the title and place, and add a caption if you like.
- **Remove**: delete the original and run the script; its entry and compressed files are removed.
- **Hide**: add `hidden: true` to the entry. The original and text are kept.
- **Order**: the gallery is sorted newest first by `date`; the order in the file does not matter.

The place lookup sends only the photo's coordinates to OpenStreetMap Nominatim; use `--no-geocode` to turn it off. The script needs Pillow and PyYAML (`pip install pillow pyyaml`).

## Local preview

On the lab server (system Ruby 2.7, no root, `$HOME` is not used), bundler and all gems live in `/scratch/cluster/haofu/envs/jekyll`, activated by `envs/jekyll.sh` (which also sets `PAGES_REPO_NWO`). One-time setup:

```sh
source /scratch/cluster/haofu/envs/jekyll.sh
gem install --no-document bundler -v 2.4.22
bundle install
```

Start the preview (from the repo root):

```sh
source /scratch/cluster/haofu/envs/jekyll.sh
bundle exec jekyll serve --host 127.0.0.1 --port 4000
```

Then forward the port to your laptop, either with VS Code's port forwarding or `ssh -L 4000:127.0.0.1:4000 <server>`, and open <http://localhost:4000>. Page and data edits reload automatically; press Ctrl+C and start it again after changing `_config.yml`.

`PAGES_REPO_NWO` is only needed locally: without it the `github-pages` gem fails with "No repo name found". Elsewhere, set it yourself and run `bundle install` / `bundle exec jekyll serve` as usual.
