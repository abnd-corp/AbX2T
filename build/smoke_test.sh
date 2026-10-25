#!/usr/bin/env bash
# AbX2T - Copyright (C) 2026 Hugo Lagouardat (Abend-core)
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Smoke test: exercises DOCX/ODT and CSV/XLSX conversions, PDF output and batch mode
# with a real Abx2t run (extraction + font generation + x2t), checking output content.
# This is the end-to-end gate for CI and for validating a machine or a bundle bump.
#
# Usage: bash build/smoke_test.sh [path/to/Abx2t]
#   Without argument, runs the project through `dotnet run` (JIT, no publish needed).
#   With an argument, tests that exact executable (e.g. the published NativeAOT exe)
#   from a fresh temp directory, exercising the first-run extraction as end users see it.

set -uo pipefail

repo=$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
sample="$repo/testdata/original/abx2t/sample.docx"
out=$(mktemp -d "${TMPDIR:-/tmp}/abx2t_smoke.XXXXXX")
trap 'rm -rf "$out"' EXIT

fail() { echo "SMOKE TEST FAILED: $1" >&2; exit 1; }

if [[ $# -ge 1 ]]; then
  # Copy the exe to a fresh dir so the first-run extraction is exercised too.
  [[ -f "$1" ]] || fail "executable not found: $1"
  cp "$1" "$out/Abx2t"
  chmod +x "$out/Abx2t"
  run() { "$out/Abx2t" "$@"; }
else
  command -v dotnet >/dev/null || fail "dotnet not found (pass a built Abx2t path instead)"
  run() { dotnet run --project "$repo/src" -c Release -- "$@"; }
fi

echo "== --version"
version=$(run --version) || fail "--version exited with $?"
echo "$version"
expected=$(sed -n 's/^ONLYOFFICE_CORE_BUILD=//p' "$repo/VERSIONS" | tr -d '\r')
[[ -n "$expected" && "$version" == *"core build $expected)"* ]] || fail "executable version does not match VERSIONS"

echo "== docx -> pdf"
run --timeout 10 "$sample" "$out/sample.pdf" || fail "docx->pdf conversion exited with $?"
[[ -f "$out/sample.pdf" ]] || fail "sample.pdf missing"
head -c 4 "$out/sample.pdf" | grep -q '%PDF' || fail "sample.pdf does not start with %PDF"
[[ $(wc -c < "$out/sample.pdf") -gt 1000 ]] || fail "sample.pdf suspiciously small"

echo "== docx -> txt"
run --timeout 10 "$sample" "$out/sample.txt" || fail "docx->txt conversion exited with $?"
grep -q "quick brown fox" "$out/sample.txt" || fail "converted text does not contain the sample sentence"

echo "== docx -> odt -> txt"
run --timeout 10 "$sample" "$out/sample.odt" || fail "docx->odt conversion failed"
run --timeout 10 "$out/sample.odt" "$out/roundtrip.txt" || fail "odt->txt conversion failed"
grep -q "quick brown fox" "$out/roundtrip.txt" || fail "ODT round-trip lost the sample sentence"

echo "== csv -> xlsx -> csv/pdf"
printf 'Name,Value\nAbx2t,42\n' > "$out/table.csv"
run --timeout 10 "$out/table.csv" "$out/table.xlsx" || fail "csv->xlsx conversion failed"
run --timeout 10 "$out/table.xlsx" "$out/roundtrip.csv" || fail "xlsx->csv conversion failed"
grep -q 'Abx2t' "$out/roundtrip.csv" || fail "XLSX round-trip lost the text cell"
grep -q '42' "$out/roundtrip.csv" || fail "XLSX round-trip lost the numeric cell"
run --timeout 10 "$out/table.xlsx" "$out/table.pdf" || fail "xlsx->pdf conversion failed"
head -c 4 "$out/table.pdf" | grep -q '%PDF' || fail "table.pdf does not start with %PDF"

echo "== batch mode"
mkdir -p "$out/batch_in" "$out/batch_out"
cp "$sample" "$out/batch_in/a.docx"
cp "$sample" "$out/batch_in/b.docx"
run --to pdf --jobs 2 "$out/batch_in/a.docx" "$out/batch_in/b.docx" "$out/batch_out" || fail "batch conversion exited with $?"
[[ -f "$out/batch_out/a.pdf" && -f "$out/batch_out/b.pdf" ]] || fail "batch outputs missing"

echo "== error paths"
run "$sample" "$sample" >/dev/null 2>&1 && fail "source==output should be refused"
[[ $? -eq 1 ]] || fail "source==output should exit 1"
run "$out/missing.docx" "$out/x.pdf" >/dev/null 2>&1
[[ $? -eq 1 ]] || fail "missing source should exit 1"

echo ""
echo "SMOKE TEST OK"
