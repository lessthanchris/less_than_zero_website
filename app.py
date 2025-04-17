#!/usr/bin/env python3

import os
import json
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

# --- Configuration ---
TEMPLATE_DIR = "templates"
DOCS_DIR = "docs"
TRACKLISTS_DIR = "tracklists"
SHOWS_FILE = "shows.json"
RELEASES_FILE = "releases.json"

TEMPLATES = {
    "index": "index.html",
    "show": "show.html",
    "archive": "archive.html",
    "calendar": "calendar.html",
    "article": "article.html",
}

# --- Ensure docs directory exists ---
os.makedirs(DOCS_DIR, exist_ok=True)

# --- Load data files ---
def load_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return []

shows = load_json(SHOWS_FILE)
releases = load_json(RELEASES_FILE)

# --- Set up Jinja2 environment ---
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    trim_blocks=True,
    lstrip_blocks=True
)

def get_template(name):
    try:
        return env.get_template(TEMPLATES[name])
    except TemplateNotFound:
        print(f"Template '{TEMPLATES[name]}' not found in {TEMPLATE_DIR}/")
        exit(1)

# --- Render index.html ---
print("Rendering index.html ...")
index_html = get_template("index").render(shows=shows)
with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(index_html)

# --- Render show pages and collect all songs ---
ALL_SONGS = []

show_template = get_template("show")
for show in shows:
    iso_date = show.get("iso_date")
    tracklist_path = os.path.join(TRACKLISTS_DIR, f"{iso_date}.json")
    try:
        with open(tracklist_path, "r", encoding="utf-8") as f:
            tracklist = json.load(f)
        for song in tracklist:
            song["date"] = iso_date
            ALL_SONGS.append(song)
    except Exception as e:
        print(f"Warning: Could not load tracklist for {iso_date}: {e}")
        tracklist = []

    show_html = show_template.render(show=show, tracklist=tracklist)
    out_path = os.path.join(DOCS_DIR, f"{iso_date}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(show_html)

# --- Render archive.html ---
print("Rendering archive.html ...")
archive_html = get_template("archive").render(ALL_SONGS=ALL_SONGS)
with open(os.path.join(DOCS_DIR, "archive.html"), "w", encoding="utf-8") as f:
    f.write(archive_html)

# --- Render calendar.html ---
print("Rendering calendar.html ...")
calendar_html = get_template("calendar").render(releases=releases)
with open(os.path.join(DOCS_DIR, "calendar.html"), "w", encoding="utf-8") as f:
    f.write(calendar_html)

# --- Render article.html ---
print("Rendering article.html ...")
article_html = get_template("article").render()
with open(os.path.join(DOCS_DIR, "article.html"), "w", encoding="utf-8") as f:
    f.write(article_html)

print("Site generation complete.")
