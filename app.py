#!/usr/bin/env python3
"""Build the Less Than Zero static site. Run: python3 app.py"""

import os
import json
import random
import re
import unicodedata
from collections import defaultdict
from datetime import datetime
from email.utils import format_datetime
from xml.sax.saxutils import escape
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = "templates"
DOCS_DIR = "docs"
TRACKLISTS_DIR = "tracklists"
SHOWS_FILE = "shows.json"
SITE_URL = "https://lessthanze.ro"

TEMPLATES = {
    "index": "index.html",
    "show": "show.html",
    "archive": "archive.html",
    "graph": "graph.html",
    "stats": "stats.html",
    "sources": "sources.html",
    "calendar": "calendar.html",
    "article": "article.html",
    "calculator": "calculator.html",
    "ai_policy": "policies/ai_policy.html",
    "second_brain": "second-brain.html",
    "artists_index": "artists_index.html",
    "artist": "artist.html",
    "404": "404.html",
}

os.makedirs(DOCS_DIR, exist_ok=True)

def load_json(fp):
    try:
        return json.load(open(fp, encoding="utf-8"))
    except Exception:
        return []

RELEASES_MD = os.environ.get(
    "LTZ_RELEASES_MD", "/home/chris/SecondBrain/LessThanZero/Releases Calendar.md"
)

def load_releases():
    """Parse the curated vault Releases Calendar table (upcoming albums
    previewed on the show). Table: | Artist | Album | Release date | First heard | Show |"""
    try:
        text = open(RELEASES_MD, encoding="utf-8").read()
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 5 or cells[0] in ("Artist", "---", ""):
            continue
        artist, album, date_str, heard, show = cells
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", date_str)
        sort_date = m.group(1) if m else date_str[:7] if re.match(r"^\d{4}-\d{2}", date_str) else "9999"
        out.append({
            "artist": artist, "album": album, "date_str": date_str,
            "sort_date": sort_date, "heard": heard, "show": show,
        })
    out.sort(key=lambda r: r["sort_date"])
    return out

shows = load_json(SHOWS_FILE)

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), trim_blocks=True, lstrip_blocks=True)

# --- Build search index ---
_COLLAB = re.compile(r"\s*(?:,|&|\+|/|\bft\.?\b|\bfeat\.?\b|\bfeaturing\b|\bversus\b|\bvs\.?\b|\bx\b|\bwith\b)\s*", re.I)

def _fold(s):
    if not s: return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.replace("&", " and ")
    return re.sub(r"[^\w]+", " ", s.lower()).strip()

def _canon(s):
    if not s: return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.replace("&", " and ")
    parts = [p for p in _COLLAB.split(s) if p.strip()]
    canon = []
    for p in parts:
        p = re.sub(r"[^\w]+", " ", p.lower()).strip()
        if p and p not in canon:
            canon.append(p)
    return " ".join(canon)

artist_index = {}
track_index = []
all_songs = []

for show in shows:
    date = show.get("iso_date")
    tl = json.load(open(os.path.join(TRACKLISTS_DIR, f"{date}.json")))
    for song in tl:
        song["date"] = date
        all_songs.append(song)
        ar = (song.get("artist") or "").strip()
        tr = (song.get("track") or "").strip()
        key = _canon(ar)
        if not key: continue
        e = artist_index.setdefault(key, {"artist": ar, "count": 0, "shows": set(), "samples": []})
        e["count"] += 1
        e["shows"].add(date)
        if tr and len(e["samples"]) < 6:
            e["samples"].append({"track": tr, "date": date})
        track_index.append({
            "artist": ar, "track": tr, "date": date,
            "_fold": _fold(f"{ar} {tr}"),
            "_artist": key,
        })

for e in artist_index.values():
    e["shows"] = sorted(e["shows"])
    e["_search"] = _canon(e["artist"]) + " " + _fold(e["artist"])

search_index = {"artists": artist_index, "tracks": track_index}
os.makedirs(os.path.join(DOCS_DIR, "static"), exist_ok=True)
with open(os.path.join(DOCS_DIR, "static", "search_index.json"), "w", encoding="utf-8") as f:
    json.dump(search_index, f, ensure_ascii=False)
print(f"Search index: {len(artist_index)} artists, {len(track_index)} tracks")

# --- Stats page data ---
def compute_stats(shows, artist_index, all_songs):
    one_timers = [e["artist"] for e in artist_index.values() if e["count"] == 1]
    most_played = max(artist_index.values(), key=lambda e: e["count"], default=None)

    # Longest streak: consecutive shows (by broadcast order, not calendar
    # gaps) an artist appeared in. shows.json is newest-first.
    order = [s.get("iso_date") for s in reversed(shows) if s.get("iso_date")]
    pos = {date: i for i, date in enumerate(order)}
    display_by_date = {s.get("iso_date"): s.get("display_date") for s in shows}
    best_artist, best_len, best_range = None, 0, None
    for e in artist_index.values():
        positions = sorted(pos[d] for d in e["shows"] if d in pos)
        if not positions:
            continue
        run_len = cur_len = 1
        run_start = cur_start = positions[0]
        for i in range(1, len(positions)):
            if positions[i] == positions[i - 1] + 1:
                cur_len += 1
            else:
                if cur_len > run_len:
                    run_len, run_start = cur_len, cur_start
                cur_len, cur_start = 1, positions[i]
        if cur_len > run_len:
            run_len, run_start = cur_len, cur_start
        if run_len > best_len:
            best_len, best_artist = run_len, e["artist"]
            best_range = (order[run_start], order[run_start + run_len - 1])

    return {
        "total_shows": len(shows),
        "total_tracks": len(all_songs),
        "distinct_artists": len(artist_index),
        "one_time_count": len(one_timers),
        "sample_one_timer": random.choice(one_timers) if one_timers else None,
        "most_played_artist": most_played["artist"] if most_played else None,
        "most_played_count": most_played["count"] if most_played else 0,
        "streak_artist": best_artist,
        "streak_len": best_len,
        "streak_start": display_by_date.get(best_range[0], best_range[0]) if best_range else None,
        "streak_end": display_by_date.get(best_range[1], best_range[1]) if best_range else None,
        "first_show": shows[-1] if shows else None,
        "latest_show": shows[0] if shows else None,
    }

stats = compute_stats(shows, artist_index, all_songs)

with open(os.path.join(DOCS_DIR, "static", "shows_list.json"), "w", encoding="utf-8") as f:
    json.dump([s.get("iso_date") for s in shows if s.get("iso_date")], f)

# --- Render pages ---
for name, tmpl in TEMPLATES.items():
    if name in ("show", "artists_index", "artist"):
        # rendered below (per-show / per-artist)
        continue
    template = env.get_template(tmpl)
    ctx = {"shows": shows, "all_songs": all_songs, "releases": load_releases(), "stats": stats}
    out = template.render(**ctx)
    out_path = os.path.join(DOCS_DIR, tmpl)
    if name == "404":
        out_path = os.path.join(DOCS_DIR, "404.html")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"  {out_path}")

# Render individual show pages
show_tmpl = env.get_template("show.html")
feed_items = []
for show in shows:
    date = show.get("iso_date")
    tl = json.load(open(os.path.join(TRACKLISTS_DIR, f"{date}.json")))
    out = show_tmpl.render(show=show, tracklist=tl)
    with open(os.path.join(DOCS_DIR, f"{date}.html"), "w", encoding="utf-8") as f:
        f.write(out)

    try:
        pub_date = datetime.strptime(date, "%Y-%m-%d").replace(hour=19)
    except (ValueError, TypeError):
        pub_date = None
    if pub_date:
        preview_artists = [t.get("artist", "") for t in tl[:3] if t.get("artist")]
        desc = f"{len(tl)} tracks"
        if preview_artists:
            desc += " — featuring " + ", ".join(preview_artists)
            if len(tl) > 3:
                desc += f" and {len(tl) - 3} more"
        feed_items.append({
            "title": show.get("display_date") or date,
            "link": f"{SITE_URL}/{date}.html",
            "pub_date": pub_date,
            "description": desc,
        })

# --- Artist pages (Encyclopedia — see ltz-admin's encyclopedia_export) ---
# Data: encyclopedia/encyclopedia.json (exported from the vault by ltz-admin).
# Pages carry an AI-transparency banner and a corrections path on every page.
import markdown as _markdown

ENCYCLOPEDIA_FILE = os.path.join(DOCS_DIR, "..", "encyclopedia", "encyclopedia.json")
if os.path.exists(ENCYCLOPEDIA_FILE):
    encyclopedia = json.load(open(ENCYCLOPEDIA_FILE, encoding="utf-8"))
    print(f"Encyclopedia: {len(encyclopedia)} artist pages")
else:
    encyclopedia = []
    print("No encyclopedia/encyclopedia.json — skipping artist pages")

_md = _markdown.Markdown(extensions=["tables"])

# --- Render artist index + per-artist pages ---
artists_index_tmpl = env.get_template("artists_index.html")
artist_tmpl = env.get_template("artist.html")
out = artists_index_tmpl.render(
    artists=encyclopedia, count=len(encyclopedia),
    total_plays=sum(a.get("plays", 0) for a in encyclopedia),
    built=encyclopedia[0]["updated"] if encyclopedia else "—",
)
with open(os.path.join(DOCS_DIR, "artists.html"), "w", encoding="utf-8") as f:
    f.write(out)
print("  docs/artists.html")

artists_dir = os.path.join(DOCS_DIR, "artists")
os.makedirs(artists_dir, exist_ok=True)
for a in encyclopedia:
    _md.reset()
    content_html = _md.convert(a["markdown"])
    out = artist_tmpl.render(
        artist=a["artist"], slug=a["slug"], content_html=content_html,
        updated=a.get("updated", ""),
    )
    with open(os.path.join(artists_dir, f"{a['slug']}.html"), "w", encoding="utf-8") as f:
        f.write(out)
print(f"  docs/artists/: {len(encyclopedia)} pages")

# --- RSS feed (recent 50 shows; no audio enclosure — see CLAUDE.md on why
# on-site listen-again is Mixcloud-only, not this feed's job) ---
feed_items.sort(key=lambda i: i["pub_date"], reverse=True)
rss = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<rss version="2.0"><channel>',
    f"<title>{escape('Less Than Zero')}</title>",
    f"<link>{SITE_URL}/</link>",
    f"<description>{escape('Weekly indie, alternative and electronica radio — live Thursdays 7-9pm UK.')}</description>",
    "<language>en-gb</language>",
]
for item in feed_items[:50]:
    rss.append("<item>")
    rss.append(f"<title>{escape(item['title'])}</title>")
    rss.append(f"<link>{escape(item['link'])}</link>")
    rss.append(f"<guid>{escape(item['link'])}</guid>")
    rss.append(f"<pubDate>{format_datetime(item['pub_date'])}</pubDate>")
    rss.append(f"<description>{escape(item['description'])}</description>")
    rss.append("</item>")
rss.append("</channel></rss>")
with open(os.path.join(DOCS_DIR, "feed.xml"), "w", encoding="utf-8") as f:
    f.write("\n".join(rss) + "\n")
print(f"RSS feed: {min(len(feed_items), 50)} items")

# --- SEO: sitemap.xml + robots.txt ---
sitemap_paths = ["", "archive.html", "graph.html", "stats.html", "sources.html", "calendar.html", "second-brain.html", "policies/ai_policy.html", "artists.html"]
sitemap_paths += [f"artists/{a['slug']}.html" for a in encyclopedia]
sitemap_paths += [f"{show.get('iso_date')}.html" for show in shows if show.get("iso_date")]

sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for path in sitemap_paths:
    sitemap.append(f"  <url><loc>{SITE_URL}/{path}</loc></url>")
sitemap.append("</urlset>")
with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
    f.write("\n".join(sitemap) + "\n")

with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
    f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")

print(f"Sitemap: {len(sitemap_paths)} URLs")
print("Done.")