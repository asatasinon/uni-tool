#!/bin/bash

# Activate virtual environment (adjust path if your venv is elsewhere)
source .venv/bin/activate

# Read JSON from stdin (not needed for this hook, but consume it)
cat > /dev/null

# Path to the temp file
temp_file=".cursor/modified_files.log"

# If the file exists, process unique paths
if [ -f "$temp_file" ]; then
  # Deduplicate paths
  unique_files=$(sort -u "$temp_file")

  # Run Ruff on each
  for file in $unique_files; do
    if [ -f "$file" ]; then
      python -m ruff check --fix --fix-only "$file" > /dev/null 2>&1 || true
      python -m ruff format "$file" > /dev/null 2>&1 || true
    fi
  done

  # Clean up
  rm "$temp_file"
fi

deactivate

# Always exit 0 for hooks
exit 0