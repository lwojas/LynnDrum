#!/bin/sh
# Builds the React UI into Source/UI/web/dist/index.html (committed: the plugin build does not need Node).
set -e
cd "$(dirname "$0")/../../Source/UI/web"
[ -d node_modules ] || npm install --no-audit --no-fund
npm run build
