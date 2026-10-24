# AbX2T - Copyright (C) 2026 Hugo Lagouardat (Abend-core)
# SPDX-License-Identifier: AGPL-3.0-or-later
#Requires -Version 5.1
<#
.SYNOPSIS
Smoke test: exercises DOCX/ODT and CSV/XLSX conversions, PDF output and batch mode.

.DESCRIPTION
Windows equivalent of build/smoke_test.sh: real Abx2t run (extraction + font
generation + x2t), end-to-end gate for CI and for validating a machine or a
bundle bump.

.PARAMETER ExePath
Path to a built Abx2t.exe. Without it, runs the project through `dotnet run`
(JIT, no publish needed). With it, the exe is copied to a fresh temp directory,
exercising the first-run extraction as end users see it.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File build\smoke_test.ps1
powershell -ExecutionPolicy Bypass -File build\smoke_test.ps1 -ExePath src\bin\x64\Release\net10.0\win-x64\publish\Abx2t.exe
#>
param(
    [string]$ExePath = ''
)

$ErrorActionPreference = 'Stop'

$repo   = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sample = Join-Path $repo 'build\testdata\sample.docx'
$out    = Join-Path $env:TEMP "abx2t_smoke_$([guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Force -Path $out | Out-Null

function Fail([string]$msg) {
    Write-Host "SMOKE TEST FAILED: $msg" -ForegroundColor Red
    Remove-Item $out -Recurse -Force -ErrorAction SilentlyContinue
    exit 1
}

if ($ExePath) {
    if (-not (Test-Path $ExePath)) { Fail "executable not found: $ExePath" }
    Copy-Item $ExePath (Join-Path $out 'Abx2t.exe')
    $runner = Join-Path $out 'Abx2t.exe'
    # Out-Host keeps the program output visible without polluting the function's
    # return stream: Run must return ONLY the exit code (a bare `& $runner` would
    # make the function return an array of output lines + code, breaking -ne 0).
    function Run { & $runner @args | Out-Host; return $LASTEXITCODE }
} else {
    if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) { Fail 'dotnet not found (pass -ExePath instead)' }
    function Run { & dotnet run --project (Join-Path $repo 'src') -c Release -- @args | Out-Host; return $LASTEXITCODE }
}

Write-Host '== --version'
if ($ExePath) {
    $version = & $runner --version
} else {
    $version = & dotnet run --project (Join-Path $repo 'src') -c Release -- --version
}
if ($LASTEXITCODE -ne 0) { Fail '--version failed' }
Write-Host $version
$expected = ((Get-Content (Join-Path $repo 'VERSIONS') | Where-Object { $_ -match '^ONLYOFFICE_CORE_BUILD=' }) -split '=', 2)[1].Trim()
if (-not $expected -or -not "$version".Contains("core build $expected)")) { Fail 'executable version does not match VERSIONS' }

Write-Host '== docx -> pdf'
$pdf = Join-Path $out 'sample.pdf'
if ((Run --timeout 10 $sample $pdf) -ne 0) { Fail 'docx->pdf conversion failed' }
if (-not (Test-Path $pdf)) { Fail 'sample.pdf missing' }
$head = [System.Text.Encoding]::ASCII.GetString((Get-Content $pdf -AsByteStream -TotalCount 4))
if ($head -ne '%PDF') { Fail 'sample.pdf does not start with %PDF' }
if ((Get-Item $pdf).Length -le 1000) { Fail 'sample.pdf suspiciously small' }

Write-Host '== docx -> txt'
$txt = Join-Path $out 'sample.txt'
if ((Run --timeout 10 $sample $txt) -ne 0) { Fail 'docx->txt conversion failed' }
if (-not (Select-String -Path $txt -Pattern 'quick brown fox' -Quiet)) { Fail 'converted text does not contain the sample sentence' }

Write-Host '== docx -> odt -> txt'
$odt = Join-Path $out 'sample.odt'
$roundtripTxt = Join-Path $out 'roundtrip.txt'
if ((Run --timeout 10 $sample $odt) -ne 0) { Fail 'docx->odt conversion failed' }
if ((Run --timeout 10 $odt $roundtripTxt) -ne 0) { Fail 'odt->txt conversion failed' }
if (-not (Select-String -Path $roundtripTxt -Pattern 'quick brown fox' -Quiet)) { Fail 'ODT round-trip lost the sample sentence' }

Write-Host '== csv -> xlsx -> csv/pdf'
$csv = Join-Path $out 'table.csv'
$xlsx = Join-Path $out 'table.xlsx'
$roundtripCsv = Join-Path $out 'roundtrip.csv'
$tablePdf = Join-Path $out 'table.pdf'
[System.IO.File]::WriteAllText($csv, "Name,Value`nAbx2t,42`n")
if ((Run --timeout 10 $csv $xlsx) -ne 0) { Fail 'csv->xlsx conversion failed' }
if ((Run --timeout 10 $xlsx $roundtripCsv) -ne 0) { Fail 'xlsx->csv conversion failed' }
if (-not (Select-String -Path $roundtripCsv -Pattern 'Abx2t' -Quiet)) { Fail 'XLSX round-trip lost the text cell' }
if (-not (Select-String -Path $roundtripCsv -Pattern '42' -Quiet)) { Fail 'XLSX round-trip lost the numeric cell' }
if ((Run --timeout 10 $xlsx $tablePdf) -ne 0) { Fail 'xlsx->pdf conversion failed' }
$head = [System.Text.Encoding]::ASCII.GetString((Get-Content $tablePdf -AsByteStream -TotalCount 4))
if ($head -ne '%PDF') { Fail 'table.pdf does not start with %PDF' }

Write-Host '== batch mode'
$batchIn  = Join-Path $out 'batch_in'
$batchOut = Join-Path $out 'batch_out'
New-Item -ItemType Directory -Force -Path $batchIn, $batchOut | Out-Null
Copy-Item $sample (Join-Path $batchIn 'a.docx')
Copy-Item $sample (Join-Path $batchIn 'b.docx')
if ((Run --to pdf --jobs 2 (Join-Path $batchIn 'a.docx') (Join-Path $batchIn 'b.docx') $batchOut) -ne 0) { Fail 'batch conversion failed' }
if (-not ((Test-Path (Join-Path $batchOut 'a.pdf')) -and (Test-Path (Join-Path $batchOut 'b.pdf')))) { Fail 'batch outputs missing' }

Write-Host '== error paths'
if ((Run $sample $sample 2>$null) -ne 1) { Fail 'source==output should exit 1' }
if ((Run (Join-Path $out 'missing.docx') (Join-Path $out 'x.pdf') 2>$null) -ne 1) { Fail 'missing source should exit 1' }
# Regression: a quoting typo (leading space in the output path) crashed with an
# unhandled IOException -> NativeAOT FailFast ("buffer overrun" system dialog).
# Leading/trailing spaces are trimmed on Windows: this must now just work.
$spaced = ' ' + (Join-Path $out 'spaced.pdf')
if ((Run --timeout 10 $sample $spaced) -ne 0) { Fail 'leading-space output path should be trimmed and succeed' }
if (-not (Test-Path (Join-Path $out 'spaced.pdf'))) { Fail 'spaced.pdf missing' }
# And a genuinely invalid path must be a clean exit 1, never a crash dialog.
if ((Run $sample 'C:\bad<>|path\out.pdf' 2>$null) -ne 1) { Fail 'invalid output path should exit 1 cleanly' }

Remove-Item $out -Recurse -Force -ErrorAction SilentlyContinue
Write-Host ''
Write-Host 'SMOKE TEST OK' -ForegroundColor Green
# Without this, pwsh propagates the $LASTEXITCODE of the last native command --
# which is the expected-failure check above (1) -- as the script exit code.
exit 0
