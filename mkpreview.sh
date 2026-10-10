#!/bin/sh
# Assembles the page (source + data) and writes a standalone copy for testing in a browser. Run from the project folder.
set -e
cd "$(dirname "$0")"
mkdir -p out site
python3 -I assemble.py page3.src.html out/data.json site/scp-constellation-map.html
python3 -I - <<'PY'
p = open("site/scp-constellation-map.html", encoding="utf-8").read()
open("out/preview.html", "w", encoding="utf-8").write('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style></head><body>' + p + '</body></html>')
PY
node -e "const s=require('fs').readFileSync('site/scp-constellation-map.html','utf8');const m=[...s.matchAll(/<script>([\s\S]*?)<\/script>/g)].pop()[1];new Function(m);console.log('script parses')"
