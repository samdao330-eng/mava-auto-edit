#!/bin/zsh
# Build the reference episode of every channel (EN + ES / PT) into <out> and check every XML.
# Run after any change in engine/ or channels/:   make test   (or tests/regression.sh [<out>])
# Speech recognition and graphics are cached in <out> (.test-output), so later runs are much faster. No video render.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
A="$ROOT/autoedit"
OUT="${1:-$ROOT/.test-output}"      # on SAM: 4K test graphics take ~15 GB, too much for a Mac's own disk
mkdir -p "$OUT"
fail=0
run() {  # <name> <autoedit args…>
  local name=$1; shift
  printf '%-6s ' "$name"
  if "$A" "$@" > "$OUT/$name.log" 2>&1; then echo "dựng xong"; else echo "LỖI (xem $OUT/$name.log)"; fail=1; fi
}
DOCS="/Volumes/SAM/0-DOCSUNTOLD/260922 Docs Untold - Patagonia"
EC="/Volumes/SAM/0-EARTHCUE/260824 Earthcue - Sierra Nevada"
TI="/Volumes/SAM/0-TRIPINSIGHT/260414 Tripinsight - Colombia"
CL="/Volumes/SAM/0-CHASELAND/260822 Chaseland - Australia"

run docs  edit "$DOCS" --out "$OUT/docs"
run ec    edit "$EC" --out "$OUT/ec"
run ec-ES lang "$EC" ES --en-work "$OUT/ec/.autoedit/_work" --out "$OUT/ec-ES"
run ti    edit "$TI" --out "$OUT/ti"
run ti-ES lang "$TI" ES --en-work "$OUT/ti/.autoedit/_work" --out "$OUT/ti-ES"
run ti-PT lang "$TI" PT --en-work "$OUT/ti/.autoedit/_work" --out "$OUT/ti-PT"
run cl    edit "$CL" --out "$OUT/cl"
"$A" check "$OUT"/*/*.xml || fail=1
exit $fail
