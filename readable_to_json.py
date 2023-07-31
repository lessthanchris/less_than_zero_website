import json
import sys

filepath = sys.argv[1]

print(filepath)

tracklist = []

with open(filepath, "r", errors="replace", encoding='utf-8') as file:
    lines = file.readlines()
    for line in lines:
        stripped_line = line.strip()
        split_line = stripped_line.split('-')
        artist = split_line[0][3:-1]
        track = '-'.join(split_line[1:])
        tracklist.append({
            "artist": artist[1:],
            "track": track[1:],
        })

file_name = filepath.split(".")[0]

with open(f"{file_name}.json", "w") as outfile:
    json.dump(tracklist, outfile, indent=2)