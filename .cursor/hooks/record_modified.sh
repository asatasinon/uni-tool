#!/bin/bash

# Activate virtual environment (adjust path if your venv is elsewhere)
source .venv/bin/activate

# Read JSON from stdin
json=$(cat)

# Extract file_path using jq
file_path=$(echo "$json" | python -c "import sys, json; print(json.load(sys.stdin)['file_path'])")

# Check if it's a Python file and append to temp list (unique via sort/uniq later)
if [[ "$file_path" == *.py ]]; then
  echo "$file_path" >> .cursor/modified_files.log
fi

# Always exit 0 for hooks
exit 0