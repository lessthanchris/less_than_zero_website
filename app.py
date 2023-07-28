#!/usr/bin/env python3

from jinja2 import Environment, FileSystemLoader
import json

with open('shows.json', 'r') as file:
    shows = json.load(file)



environment = Environment(loader=FileSystemLoader("templates/"))
template = environment.get_template("index.html")
show_template = environment.get_template("show.html")

content = template.render(shows=shows)
with open('docs/index.html', mode="w", encoding="utf-8") as message:
    message.write(content)

for show in shows:
    content = show_template.render(show=show)
    with open(f"docs/{show['iso_date']}.html", mode="w", encoding="utf-8") as file:
        file.write(content)