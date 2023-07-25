#!/usr/bin/env python3

from jinja2 import Environment, FileSystemLoader
import json

with open('shows.json', 'r') as file:
    shows = json.load(file)

print(shows)

environment = Environment(loader=FileSystemLoader("templates/"))
template = environment.get_template("index.html")

content = template.render(shows=shows)
with open('build/index.html', mode="w", encoding="utf-8") as message:
    message.write(content)