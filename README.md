# Less Than Zero — lessthanze.ro

Static site for **Less Than Zero**, a licensed UK radio show (indie/alt/
electronica, live Thursdays 7–9pm, Shetland). Built with Jinja2, deployed
via GitHub Pages — pushing to `main` makes a change live.

## Quick start

```bash
python3 app.py          # rebuild the whole site into docs/
```

That's the only command you need for routine edits: add/edit a show in
`shows.json`, add its `tracklists/{iso_date}.json` and the two
`docs/images/{iso_date}[.thumbnail].jpg` files, then rebuild.

**After a show airs**, the fast path is the interactive wizard:

```bash
python3 prepare_assets.py
```

Drop `asset_drop/{iso_date}.png` (tile art) and `asset_drop/{iso_date}.txt`
(numbered tracklist) in first — it walks you through the rest (Mixcloud
name, Patreon ID, Qobuz playlist generation, etc.) and rebuilds the site
for you. See `CLAUDE.md` for the full manual steps this automates, and the
compliance rules around when a show's page can go live.

## What's here

| Path | What |
|---|---|
| `app.py` | The build — renders `templates/*.html` → `docs/*.html`, builds the search index, sitemap, RSS feed |
| `prepare_assets.py` | Interactive wizard for turning an aired show's assets into a live update |
| `played_archive.py` | CLI for querying play history (`search` / `top` / `crosscheck`) |
| `build_graph.py` | Rebuilds the `/graph.html` artist-network data (needs `venv/`, see below) |
| `shows.json` | One entry per show, newest first |
| `tracklists/` | One JSON file per show |
| `docs/` | The committed, deployed output — GitHub Pages serves this directly |

## Setup

`app.py` and `prepare_assets.py` need `Jinja2`, `rich`, and `Pillow`
installed **globally** (`pip install --user jinja2 rich pillow`) — no venv,
by design, since `prepare_assets.py` shells out to `python3 app.py` with
its own interpreter.

`build_graph.py` is the one exception — it needs `networkx`, installed into
a local `venv/`:

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python build_graph.py
```

## An admin console for all of this

`~/Code/ltz-admin` (a sibling repo) wraps this repo's `prepare_assets.py`
and `played_archive.py` — plus crate-digger, the AI music-video pipeline,
and the now-playing overlay — behind one menu. See its own README/CLAUDE.md
if you'd rather drive everything from there.

Full workflow details, compliance rules, and design conventions: see
`CLAUDE.md`.
