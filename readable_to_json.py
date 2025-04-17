#!/usr/bin/env python3
import json
import sys
import os

def usage():
    print("Usage: python3 readable_to_json.py <input_file.txt>")
    sys.exit(1)

def parse_track_line(line):
    """
    Parses a line of the format '01. Artist - Track Title'
    Returns a dict with 'artist' and 'track', or None if parsing fails.
    """
    # Remove leading/trailing whitespace and skip empty lines
    line = line.strip()
    if not line:
        return None

    # Attempt to split on the first dash (various dash types)
    for dash in [' - ', ' – ', ' — ', '-', '–', '—']:
        if dash in line:
            parts = line.split(dash, 1)
            break
    else:
        print(f"Warning: Could not parse line (no dash found): {line}")
        return None

    # Remove track number prefix (e.g., '01. ')
    artist = parts[0].lstrip('0123456789. ').strip()
    track = parts[1].strip()
    if not artist or not track:
        print(f"Warning: Could not parse line (missing artist or track): {line}")
        return None

    return {"artist": artist, "track": track}

def main():
    if len(sys.argv) != 2:
        usage()

    filepath = sys.argv[1]

    if not os.path.isfile(filepath):
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    print(f"Parsing tracklist: {filepath}")

    tracklist = []
    with open(filepath, "r", encoding="utf-8", errors="replace") as file:
        for line in file:
            entry = parse_track_line(line)
            if entry:
                tracklist.append(entry)

    if not tracklist:
        print("No valid track entries found. Exiting.")
        sys.exit(1)

    base, _ = os.path.splitext(filepath)
    output_file = f"{base}.json"

    with open(output_file, "w", encoding="utf-8") as outfile:
        json.dump(tracklist, outfile, indent=2, ensure_ascii=False)

    print(f"Tracklist written to: {output_file}")

if __name__ == "__main__":
    main()
