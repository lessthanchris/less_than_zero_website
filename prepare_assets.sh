#!/usr/bin/env bash

echo "Preparing show assets"

convert -resize 500x500 docs/images/$1.png docs/images/$1.thumbnail.png
cwebp docs/images/$1.png -o docs/images/$1.png.webp -resize 500 0 -q 100
python3 readable_to_json.py $1.txt
rm $1.txt
mv $1.json tracklists/