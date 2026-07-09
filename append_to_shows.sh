#!/usr/bin/env bash
set -euo pipefail

# --- Color Setup ---
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${CYAN}${1}${RESET}"; }
success() { echo -e "${GREEN}${1}${RESET}"; }
warn()    { echo -e "${YELLOW}${1}${RESET}"; }
error()   { echo -e "${RED}${1}${RESET}"; }
bold()    { echo -e "${BOLD}${1}${RESET}"; }

# --- Usage ---
usage() {
    echo "Usage: $0 <iso_date> <display_date> <mixcloud_name> <patreon> <spotify_id>"
    exit 1
}

# --- Validate Arguments ---
if [[ $# -ne 5 ]]; then
    error "Error: Incorrect number of arguments."
    usage
fi

iso_date="$1"
display_date="$2"
mixcloud_name="$3"
patreon="$4"
spotify_id="$5"

# --- Validate jq ---
if ! command -v jq >/dev/null 2>&1; then
    error "Error: jq is not installed. Please install jq and retry."
    exit 1
fi

# --- Validate iso_date format ---
if ! [[ "$iso_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    error "Error: iso_date must be in yyyy-mm-dd format."
    exit 1
fi

# --- File Setup ---
EXISTING_JSON_FILE="shows.json"
BACKUP_FILE="shows.json.bak.$(date +%Y%m%d%H%M%S)"

if [[ ! -f "$EXISTING_JSON_FILE" ]]; then
    warn "$EXISTING_JSON_FILE not found. Creating a new one."
    echo "[]" > "$EXISTING_JSON_FILE"
fi

# --- Build JSON Object ---
info "Building new show object..."
new_object=$(jq -n \
    --arg iso_date "$iso_date" \
    --arg display_date "$display_date" \
    --arg mixcloud_name "$mixcloud_name" \
    --arg patreon "$patreon" \
    --arg spotify_id "$spotify_id" \
    --arg soundcloud_id "" \
    '{
        iso_date: $iso_date,
        display_date: $display_date,
        mixcloud_name: $mixcloud_name,
        patreon: $patreon,
        spotify_id: $spotify_id,
        soundcloud_id: $soundcloud_id
    }'
)

# --- Backup ---
cp "$EXISTING_JSON_FILE" "$BACKUP_FILE"
success "Backup created at $BACKUP_FILE."

# --- Prepend New Object ---
info "Prepending new show to $EXISTING_JSON_FILE..."
tmp_result=$(mktemp)
jq --argjson new "$new_object" \
   '. as $orig | [$new] + $orig' \
   "$EXISTING_JSON_FILE" > "$tmp_result"

mv "$tmp_result" "$EXISTING_JSON_FILE"
success "Prepended new object to $EXISTING_JSON_FILE successfully."

exit 0
