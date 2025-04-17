#!/bin/bash

set -e

iso_date=$1
display_date=$2
mixcloud_name=$3
patreon=$4
spotify_id=$5

TMP_OBJECT_FILE=$(mktemp)
TMP_RESULT_FILE=$(mktemp)

# Check jq is installed
if ! command -v jq >/dev/null 2>&1; then
    echo "Error: jq is not installed." >&2
    exit 1
fi

JSON_OBJ="{"
field="iso_date"
value=${iso_date}
value_escaped=$(printf '%s' "$value" | sed 's/"/\\"/g')
JSON_OBJ+="\"$field\":\"$value_escaped\""
JSON_OBJ+=","
field="display_date"
value=${display_date}
value_escaped=$(printf '%s' "$value" | sed 's/"/\\"/g')
JSON_OBJ+="\"$field\":\"$value_escaped\""
JSON_OBJ+=","
field="mixcloud_name"
value=${mixcloud_name}
value_escaped=$(printf '%s' "$value" | sed 's/"/\\"/g')
JSON_OBJ+="\"$field\":\"$value_escaped\""
JSON_OBJ+=","
field="patreon"
value=${patreon}
value_escaped=$(printf '%s' "$value" | sed 's/"/\\"/g')
JSON_OBJ+="\"$field\":\"$value_escaped\""
JSON_OBJ+=","
field="spotify_id"
value=${spotify_id}
value_escaped=$(printf '%s' "$value" | sed 's/"/\\"/g')
JSON_OBJ+="\"$field\":\"$value_escaped\""
JSON_OBJ+=","
field="soundcloud_id"
value=""
value_escaped=$(printf '%s' "$value" | sed 's/"/\\"/g')
JSON_OBJ+="\"$field\":\"$value_escaped\""
JSON_OBJ+="}"

# Write the new object to a temp file
echo "$JSON_OBJ" | jq '.' > "$TMP_OBJECT_FILE"

EXISTING_JSON_FILE="shows.json"

# Prepend the object
jq -s '.[0] as $new | .[1] as $orig | [$new] + $orig' \
    "$TMP_OBJECT_FILE" "$EXISTING_JSON_FILE" > "$TMP_RESULT_FILE"

# Overwrite the original file
mv "$TMP_RESULT_FILE" "$EXISTING_JSON_FILE"
rm "$TMP_OBJECT_FILE"

echo "Prepended new object to $EXISTING_JSON_FILE successfully."
