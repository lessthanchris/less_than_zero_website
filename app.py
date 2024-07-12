#!/usr/bin/env python3

from jinja2 import Environment, FileSystemLoader
import json

with open('shows.json', 'r') as file:
    shows = json.load(file)

with open('releases.json', 'r') as file:
    releases = json.load(file)

environment = Environment(loader=FileSystemLoader("templates/"), trim_blocks=True, lstrip_blocks=True)
template = environment.get_template("index.html")
show_template = environment.get_template("show.html")
archive_template = environment.get_template("archive.html")
calendar_template = environment.get_template("calendar.html")

ALL_SONGS = []

content = template.render(shows=shows)
with open('docs/index.html', mode="w", encoding="utf-8") as message:
    message.write(content)

content = template.render

for show in shows:
    try:
        with open(f"tracklists/{show['iso_date']}.json", mode="r") as file:
            tracklist = json.load(file)
            for song in tracklist:
                song['date'] = show['iso_date']
                ALL_SONGS.append(song)
    except Exception as e:
        print("Something went wrong opening tracklist")
        print(e)
        tracklist = []

    content = show_template.render(show=show, tracklist=tracklist)
    with open(f"docs/{show['iso_date']}.html", mode="w", encoding="utf-8") as file:
        file.write(content)

content = archive_template.render(ALL_SONGS=ALL_SONGS)
with open(f"docs/archive.html", mode="w", encoding="utf-8") as file:
    file.write(content)

content = calendar_template.render(releases=releases)
with open(f"docs/calendar.html", mode="w", encoding="utf-8") as file:
    file.write(content)