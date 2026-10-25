#!/usr/bin/env python3
"""Exercise the public CLI, batch behavior, shell entrypoints and subprocess errors."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from corpus_test import REPO, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=REPO / "dist/cli-tests")
    parser.add_argument("--test-timeout", action="store_true", help="Unix: verify the real one-minute timeout and child cleanup")
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error("Executable missing")
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("Use an empty output directory")
    output.mkdir(parents=True, exist_ok=True)
    cases = []
    skipped = []

    def check(name, command, expected=0, contains=None, files=()):
        result = run([str(part) for part in command])
        errors = []
        if result["exit_code"] != expected:
            errors.append(f"Expected exit {expected}, got {result['exit_code']}")
        if contains and contains not in result["stdout"] + result["stderr"]:
            errors.append(f"Expected diagnostic absent: {contains}")
        for path in files:
            if not path.is_file() or not path.read_bytes().startswith(b"%PDF-"):
                errors.append(f"Missing/invalid PDF: {path.name}")
        cases.append({"id": name, "run": result, "errors": errors})
        print(f"{name}: {'FAIL: ' + '; '.join(errors) if errors else 'OK'}", flush=True)

    with tempfile.TemporaryDirectory(prefix="abx2t_cli_") as temporary:
        root = Path(temporary)
        exe = root / ("Abx2t.exe" if args.exe.suffix.lower() == ".exe" else "Abx2t")
        shutil.copy2(args.exe.resolve(), exe)
        sample = root / "entrée avec espaces.docx"
        shutil.copyfile(REPO / "build/testdata/sample.docx", sample)
        source_hash = hashlib.sha256(sample.read_bytes()).hexdigest()
        for option in ("--help", "-h", "-?", "--version", "--license", "--licence", "--about"):
            check("information:" + option, [exe, option], contains="ONLYOFFICE" if option not in ("--help", "-h", "-?") else "Usage:")
        for name, arguments in [
            ("no-arguments", []), ("unknown-option", ["--unknown"]),
            ("missing-to", ["--to"]), ("missing-jobs", ["--jobs"]),
            ("jobs-zero", ["--jobs", "0"]), ("jobs-over-limit", ["--jobs", "17"]),
            ("jobs-invalid", ["--jobs", "abc"]), ("missing-timeout", ["--timeout"]),
            ("negative-timeout", ["--timeout", "-1"]),
            ("invalid-timeout", ["--timeout", "abc"]),
            ("missing-input", [root / "absent.docx", root / "missing.pdf"]),
            ("same-source-output", [sample, sample]),
            ("unsupported-output", [sample, root / "bad.xyz"]),
            ("empty-wildcard", [root / "absent-*.docx", root / "empty.pdf"]),
            ("directory-without-format", [sample, root]),
            ("unsupported-batch-format", ["--to", "unknown", sample, root / "batch-bad"]),
        ]:
            check(name, [exe, *arguments], expected=1)
        bad_extension = root / "source.xyz"
        bad_extension.write_text("unsupported source", encoding="utf-8")
        check("unsupported-input", [exe, bad_extension, root / "bad-input.pdf"], expected=1)
        direct = root / "sortie avec espaces.pdf"
        check("unicode-and-spaces", [exe, sample, direct], files=[direct])
        upper = root / "UPPER.DOCX"
        shutil.copyfile(sample, upper)
        upper_pdf = root / "UPPER.PDF"
        check("uppercase-extensions-timeout-disabled", [exe, "--timeout", "0", upper, upper_pdf], files=[upper_pdf])
        for option in ("--verbose", "-v"):
            pdf = root / (option.lstrip("-") + ".pdf")
            check("verbose:" + option, [exe, option, sample, pdf], files=[pdf])
        inputs = root / "batch-input"
        inputs.mkdir()
        for name in ("a.docx", "b.docx"):
            shutil.copyfile(sample, inputs / name)
        batch = root / "batch-output"
        check("parallel-batch-literal-wildcard", [exe, "--to", ".PDF", "--jobs", "2", inputs / "*.docx", batch],
              contains="2/2", files=[batch / "a.pdf", batch / "b.pdf"])
        serial = root / "serial-output"
        check("serial-batch", [exe, "--to", "pdf", "--jobs", "1", inputs / "a.docx", inputs / "b.docx", serial],
              contains="2/2", files=[serial / "a.pdf", serial / "b.pdf"])
        max_jobs = root / "max-jobs-output"
        check("max-jobs", [exe, "--to", "pdf", "--jobs", "16", inputs / "a.docx", max_jobs], files=[max_jobs / "a.pdf"])
        other = root / "collision"
        other.mkdir()
        shutil.copyfile(sample, other / "a.docx")
        collision = root / "collision-output"
        check("batch-output-collision", [exe, "--to", "pdf", inputs / "a.docx", other / "a.docx", collision], expected=1)
        if any(collision.glob("*.pdf")):
            cases[-1]["errors"].append("Collision refusal produced output files")
        corrupt = inputs / "corrupt.docx"
        corrupt.write_bytes(b"PK\x03\x04not-a-valid-office-archive\x00\x00")
        check("conversion-error", [exe, corrupt, root / "corrupt.pdf"], expected=2)
        partial = root / "partial-batch"
        check("partial-batch-failure", [exe, "--to", "pdf", "--jobs", "2", inputs / "a.docx", corrupt, partial],
              expected=2, contains="1 failed", files=[partial / "a.pdf"])
        if hashlib.sha256(sample.read_bytes()).hexdigest() != source_hash:
            cases.append({"id": "source-preserved", "errors": ["Source content was modified"]})
        if os.name != "nt":
            engine = root / "resources/x2t"
            backup = root / "resources/x2t.real"
            engine.rename(backup)
            try:
                engine.write_text("#!/bin/sh\nexit 7\n", encoding="utf-8")
                engine.chmod(0o755)
                check("child-exit-code", [exe, sample, root / "child-error.pdf"], expected=2, contains="exit code 7")
                engine.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                check("successful-child-without-output", [exe, sample, root / "no-output.pdf"], expected=2, contains="output file is missing")
                if args.test_timeout:
                    engine.write_text('#!/bin/sh\nprintf "%s" "$$" > timeout-child.pid\nexec /bin/sleep 90\n', encoding="utf-8")
                    started = time.monotonic()
                    check("one-minute-timeout", [exe, "--timeout", "1", sample, root / "timeout.pdf"], expected=3, contains="timed out")
                    if not 55 <= time.monotonic() - started < 85:
                        cases[-1]["errors"].append("Timeout duration was outside the expected range")
                    pid = int((engine.parent / "timeout-child.pid").read_text())
                    try:
                        os.kill(pid, 0)
                        cases[-1]["errors"].append("Timed-out child process is still alive")
                    except ProcessLookupError:
                        pass
            finally:
                engine.unlink(missing_ok=True)
                backup.rename(engine)
        else:
            skipped.append("Unix subprocess exit/missing-output/timeout fixtures; Windows uses the real engine error test")
        if not args.test_timeout:
            skipped.append("One-minute timeout not requested")

    # Validate the actual repository scripts without executing build/download side effects.
    for folder in (REPO / "build", REPO / "allfontsgen/build/scripts", REPO / "x2t/build/scripts"):
        for script in sorted(folder.glob("*.sh")):
            shell = "zsh" if "zsh" in script.read_text(encoding="utf-8").splitlines()[0] else "bash"
            if shutil.which(shell):
                check("syntax:" + str(script.relative_to(REPO)), [shell, "-n", script])
            else:
                skipped.append(f"{shell} absent: {script.relative_to(REPO)}")
    for script, shell in (("build/fetch_onlyoffice_linux.sh", "bash"), ("build/fetch_onlyoffice_macos.sh", "zsh")):
        if shutil.which(shell):
            check("help:" + script, [shell, REPO / script, "--help"], contains="Usage:")
            check("invalid-option:" + script, [shell, REPO / script, "--not-an-option"], expected=1)
    if shutil.which("pwsh"):
        command = "$errorsFound = @(); Get-ChildItem -Path build,allfontsgen/build/scripts,x2t/build/scripts -Filter *.ps1 | ForEach-Object { $tokens = $null; $parseErrors = $null; [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null; $errorsFound += $parseErrors }; if ($errorsFound.Count) { $errorsFound | Out-String | Write-Error; exit 1 }; exit 0"
        result = subprocess.run(["pwsh", "-NoProfile", "-Command", command], cwd=REPO, capture_output=True)
        cases.append({"id": "powershell-syntax", "errors": [] if result.returncode == 0 else [result.stderr.decode(errors="replace")]})
    else:
        skipped.append("PowerShell syntax: pwsh not installed")
    report = {"checks": cases, "skipped": skipped,
              "not_covered": ["Live UNC/SMB shares", "Unwritable install directory fallback on every OS"],
              "passed": all(not case["errors"] for case in cases)}
    (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(cases)} checks; {sum(bool(c['errors']) for c in cases)} failures; {len(skipped)} explicit skips", flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
