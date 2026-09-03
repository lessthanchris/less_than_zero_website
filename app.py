#!/usr/bin/env python3
"""Build the Less Than Zero static site. Run: python3 app.py"""

import os
import json
import re
import unicodedata
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = "templates"
DOCS_DIR = "docs"
TRACKLISTS_DIR = "tracklists"
SHOWS_FILE = "shows.json"

TEMPLATES = {
    "index": "index.html",
    "show": "show.html",
    "archive": "archive.html",
    "calendar": "calendar.html",
    "article": "article.html",
    "calculator": "calculator.html",
    "ai_policy": "policies/ai_policy.html",
    "second_brain": "second-brain.html",
    "404": "404.html",
}

os.makedirs(DOCS_DIR, exist_ok=True)

def load_json(fp):
    try:
        return json.load(open(fp, encoding="utf-8"))
    except Exception:
        return []

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

# --- Render pages ---
for name, tmpl in TEMPLATES.items():
    if name == "show":
        # Show pages are rendered per-show below
        continue
    template = env.get_template(tmpl)
    ctx = {"shows": shows, "all_songs": all_songs, "releases": {}}
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
for show in shows:
    date = show.get("iso_date")
    tl = json.load(open(os.path.join(TRACKLISTS_DIR, f"{date}.json")))
    out = show_tmpl.render(show=show, tracklist=tl)
    with open(os.path.join(DOCS_DIR, f"{date}.html"), "w", encoding="utf-8") as f:
        f.write(out)

# --- SEO: sitemap.xml + robots.txt ---
SITE_URL = "https://lessthanze.ro"
sitemap_paths = ["", "archive.html", "calendar.html", "second-brain.html", "policies/ai_policy.html"]
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