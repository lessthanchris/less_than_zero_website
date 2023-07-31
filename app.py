#!/usr/bin/env python3

from jinja2 import Environment, FileSystemLoader
import json

with open('shows.json', 'r') as file:
    shows = json.load(file)



environment = Environment(loader=FileSystemLoader("templates/"), trim_blocks=True, lstrip_blocks=True)
template = environment.get_template("index.html")
show_template = environment.get_template("show.html")

content = template.render(shows=shows)
with open('docs/index.html', mode="w", encoding="utf-8") as message:
    message.write(content)

for show in shows:
    try:
        with open(f"tracklists/{show['iso_date']}.json", mode="r") as file:
            tracklist = json.load(file)
    except:
        print("Something went wrong opening tracklist")
        tracklist = []

    content = show_template.render(show=show, tracklist=tracklist)
    with open(f"docs/{show['iso_date']}.html", mode="w", encoding="utf-8") as file:
        file.write(content)