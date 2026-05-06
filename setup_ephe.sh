#!/bin/bash
# Download Swiss Ephemeris data files needed for calculations
mkdir -p /app/ephe
cd /app/ephe

# Download essential ephemeris files (covers years 1800-2400)
BASE="https://raw.githubusercontent.com/aloistr/swisseph/master/ephe"

files=(
  "seas_18.se1"
  "sepl_18.se1"
  "semo_18.se1"
)

for f in "${files[@]}"; do
  if [ ! -f "$f" ]; then
    echo "Downloading $f..."
    curl -sL "$BASE/$f" -o "$f" || echo "Warning: could not download $f"
  fi
done

echo "Ephemeris files ready."
