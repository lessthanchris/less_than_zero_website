# Less Than Zero — lessthanze.ro

Static site for Less Than Zero, a licensed UK radio show (indie/alt/electronica,
live Thursdays 7-9pm, Shetland). Built with Jinja2 (`app.py` → `docs/`), deployed
via GitHub Pages (`docs/` on `main`, custom domain via `docs/CNAME`) — pushing to
`main` is what makes a change live.

## Repo layout

- `app.py` — the build. Renders `templates/*.html` → `docs/*.html`, builds
  `docs/static/search_index.json` from `tracklists/`, generates `sitemap.xml`/`robots.txt`.
  Only dependency is Jinja2 (installed globally, no venv/requirements needed for this).
- `shows.json` — one entry per show (154+), **newest first**. Fields: `iso_date`,
  `display_date`, `mixcloud_name`, `patreon`, `spotify_id`, `qobuz_id`,
  `soundcloud_id` (dead field, not used in any template — ignore it).
  `spotify_id`/`qobuz_id` treat `"", "na", "nah", "0", "blah", "999"` as blank
  (sentinel junk values from earlier manual data entry — guard against them the
  same way `show.html` does if you add new logic touching these fields).
- `tracklists/{iso_date}.json` — one file per show, a flat list of
  `{"artist": ..., "track": ...}` in play order. **Required** for every show in
  `shows.json` — `app.py` hard-crashes (`FileNotFoundError`) if one's missing.
- `docs/images/{iso_date}.jpg` (800×800 tile art) and
  `{iso_date}.thumbnail.jpg` (400×400) — both required per show.
- `docs/static/` — mix of hand-maintained (`site.css`, `search.css`, `search.js`,
  `player.js`, `graph.js`, `graph.css`) and generated (`search_index.json`,
  `graph.json`) files. `app.py` does not copy a separate `static/` source dir —
  everything under `docs/static/` is either edited there directly or generated
  in place.
- `build_graph.py` — separate, manually-run script (not part of `app.py`'s
  build) that builds the `/graph.html` artist-network data. Needs `networkx`
  (`requirements.txt`, install into `venv/`, gitignored) — not needed for
  routine site edits, only for refreshing the graph.
- `played_archive.py` — standalone CLI for querying play history
  (`python3 played_archive.py search "<artist>"` / `top` / `crosscheck`).
  Owns the canonical artist-name normalization (`_canon`, `_COLLAB` regex,
  mojibake repair) that `build_graph.py` reuses — reuse it too rather than
  re-implementing name matching/normalization.
- `prepare_assets.py` — interactive wizard (rich) that turns an
  `asset_drop/{iso_date}` drop into a live show update in one step; see
  "Updating the site after a show airs" below. Needs `rich` + `Pillow`
  installed globally (same as `app.py` needs Jinja2) — run it as plain
  `python3 prepare_assets.py`, never via `venv/bin/python3` (it shells out to
  `python3 app.py` with its own interpreter, and `venv/` only has networkx).
- `asset_drop/` — gitignored scratch folder for raw per-show materials
  dropped in ahead of `prepare_assets.py`: `{iso_date}.png` (tile art),
  `{iso_date}.txt` (numbered tracklist, `NN. Artist - Track` per line),
  `{iso_date}.mkv` (the recording, optional). Can hold multi-GB files —
  never add these to git directly.

## Updating the site after a show airs

**Fast path**: drop `asset_drop/{iso_date}.png` (tile art) and
`asset_drop/{iso_date}.txt` (numbered tracklist) — plus optionally
`asset_drop/{iso_date}.mkv`, the recording — then run:

```
python3 prepare_assets.py
```

It walks you through: picking the date (if ambiguous), previewing the
parsed tracklist, filling in `mixcloud_name`/`patreon`/`qobuz_id`/`spotify_id`
(blank is fine — leave for later), optionally extracting an mp3 from the
`.mkv` for manual Patreon upload, then does everything in steps 1-6 below in
one go: writes `tracklists/{iso_date}.json`, builds the 800×800/400×400 jpgs,
inserts the `shows.json` entry, rebuilds the site, and refreshes the artist
graph. Any field left blank can be filled in later with
`python3 prepare_assets.py {iso_date} --force`. It never commits or pushes —
that's still on you (step 7). Non-interactive/scripted use: `-y` plus
`--mixcloud-name`/`--patreon`/`--qobuz-id`/`--spotify-id`/`--no-graph`/`--no-mp3`.

**What that automates, or do by hand if `asset_drop/` inputs aren't available**:

1. **Add the show to `shows.json`** at the top of the list (newest-first).
   Minimum: `iso_date`, `display_date`. Fill in `mixcloud_name`/`patreon` once
   those are posted (may be a day or two after the show); `qobuz_id` once
   crate-digger's pushed a playlist for it (see below).
2. **Add `tracklists/{iso_date}.json`** — the actual tracklist that aired.
3. **Add the two images**: `docs/images/{iso_date}.jpg` (800×800) and
   `docs/images/{iso_date}.thumbnail.jpg` (400×400).
4. **Rebuild**: `python3 app.py` — regenerates every page, the search index,
   sitemap, and robots.txt. Do this even for small metadata-only edits to
   `shows.json` (e.g. adding a `mixcloud_name` after the fact); `docs/*.html`
   is committed output, not generated at deploy time, so it goes stale if you
   edit source files without rebuilding.
5. **Refresh the evergreen playlists** (optional but nice — keeps the "always
   current show" Qobuz/Spotify playlists linked from the homepage/footer
   actually current; `prepare_assets.py` doesn't do this one). From
   `~/crate-digger`:
   ```
   python -m crate_digger evergreen --tracklist /path/to/tracklists/{iso_date}.json
   ```
   This is **not** the same as `dig --qobuz-evergreen`/`--spotify-evergreen` —
   those refresh evergreen from `dig`'s own upcoming-release prep candidates,
   not from a specific aired show. Use plain `evergreen` here.
6. **Refresh the artist graph periodically** (not required every week — the
   overall shape barely shifts from one show): `pip install -r requirements.txt`
   into `venv/` once, then `venv/bin/python build_graph.py`.
7. **Commit and push** — `git add` the specific files touched (avoid `git add -A`;
   this repo doesn't gitignore build output, so a broad add can also sweep up
   unrelated local scratch files). Push to `main` to go live.

**Compliance — do not skip**: this show is PPL/PRS licensed for UK-only
webcasting (see `~/SecondBrain/LessThanZero/Licensing.md` and the PDFs beside
it for the actual licence terms if anything here seems ambiguous — read the
primary documents, not just this summary, before assuming a rule).
Load-bearing rules for site/data work specifically:
- **Never commit or push a show's tracklist/page before that show has aired.**
  Pre-announcing exact tracklists/artists ahead of broadcast is a licence
  violation. Prepping a page in advance is fine as long as it isn't pushed live.
- Track repeat limits (≤4 by one artist / ≤3 from one album per rolling
  3-hour window, no exact track repeat within 1 hour) apply to the
  **broadcast/playout**, not the website — not something to enforce here, but
  useful context if `tracklists/*.json` ever looks like it's violating them
  (may indicate a data entry error worth flagging rather than silently fixing).

## Design conventions

Light theme throughout (`docs/static/site.css` owns the design tokens: `--accent`
teal `#0f9b8e` for the site's own CTAs/accents, Discord's actual brand blurple
`#5865F2` — `.btn-discord` — reserved specifically for Discord links so it
doesn't get diluted into a generic "primary" color). Montserrat for headings,
Nunito for body text. Funnel hierarchy across CTAs: instant on-site listen
(the persistent player, `#ltz-player` in `base.html` / `player.js`) → Discord
(capture) → Mixcloud (archive browsing) → Patreon (downstream, never a
first-touch ask). Qobuz/Spotify evergreen playlists are content/SEO
value-add, kept deliberately low-key (a single muted line, not a promoted CTA).

`templates/base.html` has a `{% block body_wrapper %}` around the standard
`.container` div and a `{% block scripts %}` before `</body>` — use these
(see `templates/graph.html`) for any page that needs to break out of the
standard container width or load extra page-specific JS, rather than
duplicating `base.html`'s structure.

## Related repo

`~/crate-digger` (no git remote currently, local only) — separate tool for
weekly show-prep (`dig`, finds candidate new releases from blogs/Bandcamp) and
for pushing playlists to Qobuz/Spotify (`dig --qobuz`/`--spotify` for prep
candidates, `evergreen` for an aired show — see above). Its own `CLAUDE.md`
doesn't exist yet; this file and its `README.md` are the current source of
truth for how the two repos relate.
