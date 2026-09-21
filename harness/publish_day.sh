#!/usr/bin/env bash
# Publish one finished day to GitHub: commits tricks/dNN, runs/dNN and plan changes, then pushes.
# Usage: harness/publish_day.sh d01
# Run it only once that day's post is live: GitHub never shows a day before X does.
# Add the day's README row (and any log entry held in private/held/HELD.md) first.
set -euo pipefail
cd "$(dirname "$0")/.."
id="${1:?usage: harness/publish_day.sh dNN}"
[[ "$id" =~ ^d[0-9]{2,3}$ ]] || { echo "id must look like d01"; exit 1; }
[ -f "runs/$id/summary.json" ] || { echo "runs/$id/summary.json missing: run python3 harness/run.py $id first"; exit 1; }
if git ls-files --others --exclude-standard | grep -q '^private/'; then echo "private/ is not ignored, refusing"; exit 1; fi
verdict=$(python3 -c "import json;print(json.load(open('runs/$id/summary.json'))['verdict'])")
[ "$verdict" != "inconclusive" ] || { echo "verdict is inconclusive: rerun before publishing"; exit 1; }
git add "tricks/$id" "runs/$id" plan PROTOCOL.md README.md
git commit -m "$id: $verdict" || echo "nothing new to commit"
git push origin HEAD
echo "https://github.com/sebuzdugan/100-tricks-lab/tree/main/runs/$id"
