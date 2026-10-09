#!/bin/bash
# Installs the Python deps the video skills need in Claude Code cloud sessions.
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0

python3 -c "import numpy" 2>/dev/null || pip install -q numpy
# Pin Playwright to the version matching the container's preinstalled Chromium (chromium-1194).
python3 -c "import playwright" 2>/dev/null || pip install -q "playwright==1.56.0"
