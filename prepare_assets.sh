#!/usr/bin/env bash

echo "Preparing show assets"
read -p "Enter Show Name: " show_name
read -p "Enter date in yyyy-mm-dd format: " iso_date
read -p "Enter date in dayth month year format: " human_date

# Creating thumbnails and webp
convert -resize 500x500 asset_drop/$iso_date.png asset_drop/$iso_date.thumbnail.png
cwebp asset_drop/$iso_date.png -o asset_drop/$iso_date.png.webp -resize 500 0 -q 100
cp asset_drop/$iso_date.png docs/images
cp asset_drop/$iso_date.thumbnail.png docs/images/ 
cp asset_drop/$iso_date.png.webp docs/images/

# Convert tracklist to JSON
python3 readable_to_json.py asset_drop/$iso_date.txt
cp asset_drop/$iso_date.json tracklists/

# Extract MP3 from MKV
# ffmpeg -i asset_drop/$iso_date.mkv -vn -c:a libmp3lame -q:a 2 asset_drop/$iso_date.mp3

# Open Patreon Upload Pages
echo "https://www.patreon.com/posts/new?postType=audio_file" | clip.exe
read -p "Go to browser, paste into url, press enter when done: "

echo "[AUDIO] $show_name | $human_date" | clip.exe
read -p "Paste into title, press enter when done: "
echo "Dive into the heart of indie music with Less Than Zero, your go-to radio show for an eclectic mix of tunes that promise to enchant, energize, and evoke emotions. Broadcasting live with passionate hosts who live and breathe music, we're here to bring you a unique auditory experience that transcends the ordinary." | clip.exe
read -p "Paste into description, press enter when done: "
read -p "Upload MP3 file, enter the post ID: " mp3_post_id

echo "https://www.patreon.com/posts/new?postType=audio_file" | clip.exe
read -p "Go to browser, paste into url, press enter when done: "

echo "[VIDEO] $show_name | $human_date" | clip.exe
read -p "Paste into title, press enter when done: "
echo "Dive into the heart of indie music with Less Than Zero, your go-to radio show for an eclectic mix of tunes that promise to enchant, energize, and evoke emotions. Broadcasting live with passionate hosts who live and breathe music, we're here to bring you a unique auditory experience that transcends the ordinary." | clip.exe
read -p "Paste into description, press enter when done: "
read -p "Upload MKV file, press enter when done: "

read -p "Please enter Mixcloud name: " mixcloud_name
read -p "Please enter Spotify ID: " spotify_id

bash append_to_shows.sh "$iso_date" "$human_date" "$mixcloud_name" "$mp3_post_id" "$spotify_id"

python3 app.py


