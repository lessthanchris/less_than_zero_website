#!/usr/bin/env bash
set -euo pipefail

# --- Color Setup ---
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

# --- Helper Functions ---

info()    { echo -e "${CYAN}${1}${RESET}"; }
success() { echo -e "${GREEN}${1}${RESET}"; }
warn()    { echo -e "${YELLOW}${1}${RESET}"; }
error()   { echo -e "${RED}${1}${RESET}"; }
bold()    { echo -e "${BOLD}${1}${RESET}"; }

prompt() {
    local varname=$1 prompt_text=$2
    read -rp "$(echo -e "${BOLD}${prompt_text}${RESET}")" "$varname"
}

clipboard() {
    # Cross-platform clipboard copy
    if command -v clip.exe &>/dev/null; then
        echo -n "$1" | clip.exe
        success "Copied to clipboard (Windows)."
    elif command -v pbcopy &>/dev/null; then
        echo -n "$1" | pbcopy
        success "Copied to clipboard (macOS)."
    elif command -v xclip &>/dev/null; then
        echo -n "$1" | xclip -selection clipboard
        success "Copied to clipboard (Linux)."
    else
        warn "Clipboard utility not found. Please copy manually:"
        echo "$1"
    fi
}

validate_iso_date() {
    [[ "$1" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]
}

file_exists_or_exit() {
    if [[ ! -f "$1" ]]; then
        error "Missing file: $1"
        exit 1
    fi
}

# --- Script Start ---

bold "=== Preparing Show Assets ==="

# Show name
prompt show_name "Enter Show Name: "

# ISO date with validation
while true; do
    prompt iso_date "Enter show date (yyyy-mm-dd): "
    if validate_iso_date "$iso_date"; then
        break
    else
        warn "Invalid date format. Please use yyyy-mm-dd."
    fi
done

# Human-readable date
prompt human_date "Enter date in 'dayth Month Year' (e.g. 17th April 2025): "

# File checks
png_file="asset_drop/$iso_date.png"
txt_file="asset_drop/$iso_date.txt"
file_exists_or_exit "$png_file"
file_exists_or_exit "$txt_file"

# --- Image Processing ---
info "Creating thumbnail and webp images..."
convert -resize 500x500 "$png_file" "asset_drop/$iso_date.thumbnail.png"
cwebp "$png_file" -o "asset_drop/$iso_date.png.webp" -resize 500 0 -q 100
success "Images created."

info "Copying images to docs/images/..."
cp "$png_file" "docs/images/"
cp "asset_drop/$iso_date.thumbnail.png" "docs/images/"
cp "asset_drop/$iso_date.png.webp" "docs/images/"
success "Images copied."

# --- Tracklist JSON ---
info "Converting tracklist to JSON..."
python3 readable_to_json.py "$txt_file"
cp "asset_drop/$iso_date.json" "tracklists/"
success "Tracklist JSON created."

# --- Optional: MP3 Extraction ---
if [[ -f "asset_drop/$iso_date.mkv" ]]; then
    prompt extract_mp3 "Extract MP3 from MKV? (y/n): "
    if [[ "$extract_mp3" =~ ^[Yy]$ ]]; then
        info "Extracting MP3..."
        ffmpeg -i "asset_drop/$iso_date.mkv" -vn -c:a libmp3lame -q:a 2 "asset_drop/$iso_date.mp3"
        success "MP3 extracted."
    fi
fi

# --- Patreon Uploads ---
description="Dive into the heart of indie music with Less Than Zero, your go-to radio show for an eclectic mix of tunes that promise to enchant, energize, and evoke emotions. Broadcasting live with passionate hosts who live and breathe music, we're here to bring you a unique auditory experience that transcends the ordinary."
patreon_url="https://www.patreon.com/posts/new?postType=audio_file"

for type in AUDIO VIDEO; do
    bold "Patreon upload: $type"
    clipboard "$patreon_url"
    prompt dummy "Open Patreon and paste URL, then press Enter to continue: "
    title="[$type] $show_name | $human_date"
    clipboard "$title"
    prompt dummy "Paste into Patreon title, then press Enter: "
    clipboard "$description"
    prompt dummy "Paste into Patreon description, then press Enter: "
    if [[ "$type" == "AUDIO" ]]; then
        prompt mp3_post_id "Upload MP3 file, then enter the Patreon post ID: "
    else
        prompt dummy "Upload MKV file, then press Enter to continue: "
    fi
done

# --- Mixcloud and Spotify ---
prompt mixcloud_name "Enter Mixcloud name: "
prompt spotify_id "Enter Spotify ID: "

# --- Append to shows ---
info "Appending show info to database..."
bash append_to_shows.sh "$iso_date" "$human_date" "$mixcloud_name" "$mp3_post_id" "$spotify_id"
success "Show info appended."

# --- Final Step: Run App ---
info "Running post-processing app..."
python3 app.py
success "All done! Your show assets are ready."

