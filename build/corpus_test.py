#!/usr/bin/env python3
"""Download pinned public fixtures, convert them and prepare a visual review.

Python standard library only. Optional Poppler tools inspect/rasterize the actual
AbX2T PDFs; macOS Quick Look previews the original Office files directly. No
second PDF conversion or reference renderer is used.
"""

import argparse
import hashlib
import html
import json
import platform
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import BadZipFile, ZipFile

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "testdata/manifest.json"
WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def run(command, timeout=150):
    started = time.monotonic()
    try:
        proc = subprocess.run(command, capture_output=True, timeout=timeout)
        return {
            "command": [str(part) for part in command],
            "exit_code": proc.returncode,
            "stdout": proc.stdout.decode("utf-8", errors="replace"),
            "stderr": proc.stderr.decode("utf-8", errors="replace"),
            "seconds": round(time.monotonic() - started, 2),
        }
    except subprocess.TimeoutExpired:
        return {"command": [str(p) for p in command], "exit_code": -1,
                "stdout": "", "stderr": "Test harness timeout",
                "seconds": round(time.monotonic() - started, 2)}


def normalize(text):
    # Ignore layout whitespace and bidi control characters when checking content.
    text = unicodedata.normalize("NFKC", text)
    return " ".join("".join(c for c in text if unicodedata.category(c) != "Cf").split())


def fetch(case, cache, offline):
    if "path" in case:
        target = MANIFEST.parent / case["path"]
        verify_source(case, target.read_bytes())
        return target
    target = cache / case["id"] / case["filename"]
    if not target.exists():
        if offline:
            raise ValueError(f"Source missing in offline mode: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + ".part")
        try:
            with urllib.request.urlopen(case["url"], timeout=60) as response:
                data = response.read(case["size"] + 1)
            verify_source(case, data)
            partial.write_bytes(data)
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)
    verify_source(case, target.read_bytes())
    return target


def verify_source(case, data):
    if len(data) != case["size"] or hashlib.sha256(data).hexdigest() != case["sha256"]:
        raise ValueError(f"Source size/SHA-256 mismatch: {case['id']}")


def requested_fonts(source, content_only=False):
    if source.suffix.lower() != ".docx":
        return []
    fonts = set()
    with ZipFile(source) as archive:
        for name in archive.namelist():
            if not name.startswith("word/") or not name.endswith(".xml"):
                continue
            if content_only and (name.startswith("word/theme/") or Path(name).name in
                                 ("styles.xml", "stylesWithEffects.xml", "fontTable.xml", "settings.xml")):
                continue
            root = ET.fromstring(archive.read(name))
            for element in root.iter(WORD_NS + "rFonts"):
                for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
                    if element.get(WORD_NS + attr):
                        fonts.add(element.get(WORD_NS + attr))
            # Resolve the theme families too, rather than assuming Times New Roman.
            if not content_only and name.startswith("word/theme/"):
                for element in root.iter():
                    if element.get("typeface"):
                        fonts.add(element.get("typeface"))
    return sorted(fonts)


def check_output(target, expected, require_tools):
    checks = []
    details = {}
    if not target.is_file():
        return ["output file missing"], details
    data = target.read_bytes()
    if target.suffix == ".pdf":
        if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
            checks.append("invalid PDF header/end marker")
        if len(data) < 1000:
            checks.append("PDF suspiciously small")
        for tool in ("pdfinfo", "pdftotext", "pdffonts"):
            if not shutil.which(tool):
                if require_tools:
                    checks.append(f"required inspection tool missing: {tool}")
                continue
            command = [tool, str(target)]
            if tool == "pdftotext":
                command += ["-"]
            result = run(command, timeout=30)
            details[tool] = result
            if result["exit_code"]:
                checks.append(f"{tool} could not inspect the PDF")
            if tool == "pdfinfo":
                match = re.search(r"^Pages:\s+(\d+)", result["stdout"], re.M)
                if match:
                    details["pages"] = int(match[1])
            if tool == "pdftotext":
                details["text_characters"] = len(normalize(result["stdout"]))
                if expected and normalize(expected) not in normalize(result["stdout"]):
                    checks.append("expected source text absent from PDF extraction")
    elif target.suffix in (".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp"):
        try:
            with ZipFile(target) as archive:
                bad = archive.testzip()
                required = "[Content_Types].xml" if target.suffix.endswith("x") else "mimetype"
                if bad or required not in archive.namelist():
                    checks.append("invalid Office/OpenDocument archive")
        except BadZipFile:
            checks.append("output is not a ZIP-based Office/OpenDocument file")
    elif target.suffix == ".txt" and expected:
        if normalize(expected) not in normalize(data.decode("utf-8-sig", errors="replace")):
            checks.append("expected source text absent from TXT conversion")
    return checks, details


def previews(source, pdf, folder, max_pages):
    details = {"source": None, "pdf": [], "notes": []}
    quicklook = shutil.which("qlmanage")
    if quicklook:
        result = run([quicklook, "-t", "-s", "1400", "-o", str(folder), str(source)], 30)
        image = folder / (source.name + ".png")
        if result["exit_code"] == 0 and image.exists():
            details["source"] = image.name
        else:
            details["notes"].append("Original preview unavailable; open the source file directly.")
    else:
        details["notes"].append("Quick Look unavailable; open the original in its Office application.")
    rasterizer = shutil.which("pdftoppm")
    if rasterizer and pdf.is_file():
        prefix = folder / "pdf-page"
        result = run([rasterizer, "-f", "1", "-l", str(max_pages),
                      "-scale-to", "1400", "-png", str(pdf), str(prefix)], 120)
        if result["exit_code"] == 0:
            details["pdf"] = [p.name for p in sorted(folder.glob("pdf-page-*.png"))]
        else:
            details["notes"].append("PDF rasterization failed; open the PDF directly.")
    else:
        details["notes"].append("Poppler previews unavailable; open the PDF directly.")
    return details


def escape(value):
    return html.escape(str(value), quote=True)


def prepare_testdata(output):
    """Use one root containing source fixtures and generated converted/results folders."""
    output.mkdir(parents=True, exist_ok=True)
    if output.resolve() == MANIFEST.parent.resolve():
        return
    for name in ("manifest.json", "ATTRIBUTIONS.md", "README.md"):
        shutil.copyfile(MANIFEST.parent / name, output / name)
    for name in ("original", "licenses", "fonts"):
        shutil.copytree(MANIFEST.parent / name, output / name, dirs_exist_ok=True)


def report_html(report, output):
    rows = []
    for case in report["cases"]:
        links = " · ".join(
            f'<a href="converted/{escape(case["id"])}/{escape(c["filename"])}">{escape(c["format"].upper())}</a>'
            for c in case["conversions"] if c.get("exists"))
        rows.append(f'<tr><td>{escape(case["title"])}</td><td><a href="{escape(case["path"])}">'
                    f'{escape(case["filename"])}</a></td><td>{links}</td></tr>')
    font_source = json.loads((output / "manifest.json").read_text(encoding="utf-8"))["font_fixture"]["document_path"]
    font_links = []
    for filename, label in (("01-missing-font.pdf", "Cas 1 : police absente"),
                            ("02-manually-added-font.pdf", "Cas 2 : police ajoutée manuellement")):
        if (output / "converted/fonts" / filename).is_file():
            font_links.append(f'<a href="converted/fonts/{filename}">{label}</a>')
    if font_links:
        rows.append(f'<tr><td>Police Fugaz One : même original, deux scénarios</td>'
                    f'<td><a href="{escape(font_source)}">fugaz-one.docx</a></td>'
                    f'<td>{" · ".join(font_links)}</td></tr>')
    document = '''<!doctype html><html lang="fr"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>AbX2T — testdata</title>
<style>body{font:16px/1.6 system-ui,sans-serif;margin:32px;color:#182238}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:12px;border-bottom:1px solid #ddd}a{color:#155ca1}</style>
<h1>Originaux et conversions</h1><p>Un seul jeu de données : <code>original/</code> et <code>converted/</code>.
Comparer directement les fichiers originaux aux sorties. Aucun PDF de référence ni verdict visuel.</p>
<p><a href="README.md">Organisation et scénarios de police</a> · <a href="ATTRIBUTIONS.md">Attributions et licences</a> · <a href="results/corpus.json">Résultats du corpus</a></p>
<table><thead><tr><th>Document</th><th>Original</th><th>Converted</th></tr></thead><tbody>'''
    document += "".join(rows) + "</tbody></table></html>"
    (output / "index.html").write_text(document, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, help="Published AbX2T executable")
    parser.add_argument("--output", type=Path, default=REPO / "testdata")
    parser.add_argument("--cache", type=Path, default=REPO / "build/cache/corpus")
    parser.add_argument("--case", action="append", dest="ids", help="Case ID; repeat to select multiple cases")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--previews", action="store_true", help="Preview original files directly and rasterize output PDFs")
    parser.add_argument("--require-pdf-tools", action="store_true", help="Require pdfinfo, pdftotext and pdffonts")
    parser.add_argument("--allow-known-content-issues", action="store_true",
                        help="Allow only exact content issues listed in the manifest; preserve every diagnostic")
    parser.add_argument("--max-preview-pages", type=int, default=20)
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cases = manifest["cases"]
    if args.ids:
        unknown = set(args.ids) - {c["id"] for c in cases}
        if unknown:
            parser.error(f"Unknown cases: {', '.join(sorted(unknown))}")
        cases = [c for c in cases if c["id"] in args.ids]
    if args.max_preview_pages < 1:
        parser.error("--max-preview-pages must be positive")
    for case in cases:
        for field in ("id", "filename"):
            if Path(case[field]).name != case[field] or case[field] in (".", ".."):
                parser.error(f"Invalid manifest path: {case[field]}")
        if "path" in case and not (MANIFEST.parent / case["path"]).resolve().is_relative_to(MANIFEST.parent.resolve()):
            parser.error(f"Source path escapes the corpus: {case['path']}")
    if not args.download_only and (not args.exe or not args.exe.is_file()):
        parser.error("--exe must point to a published AbX2T executable")
    output = args.output.resolve()
    prepare_testdata(output)
    (output / "results").mkdir(exist_ok=True)
    report = {"platform": platform.platform(), "python": platform.python_version(),
              "visual_fidelity": "manual review required; no reference PDF",
              "max_preview_pages": args.max_preview_pages, "cases": []}
    if not args.download_only:
        args.exe = args.exe.resolve()
        report["version"] = run([str(args.exe), "--version"], timeout=30)
        if report["version"]["exit_code"]:
            parser.error("AbX2T --version failed")
    failed = 0
    blocking_failures = 0
    for case in cases:
        print(f"== {case['id']}: {case['filename']}", flush=True)
        folder = output / "converted" / case["id"]
        if folder.is_symlink():
            parser.error(f"Generated output must not be a symlink: {folder}")
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        entry = dict(case, conversions=[], errors=[], blocking_errors=[])
        try:
            verified = fetch(case, args.cache.resolve(), args.offline)
            source = output / case["path"]
            if verified.resolve() != source.resolve():
                shutil.copyfile(verified, source)
            verify_source(case, source.read_bytes())
            entry["requested_fonts"] = requested_fonts(source)
            entry["content_fonts"] = requested_fonts(source, content_only=True)
            if not args.download_only:
                for extension in case["outputs"]:
                    target = folder / (source.stem + "-converted." + extension)
                    result = run([str(args.exe), "--timeout", "2", str(source), str(target)])
                    errors, inspection = check_output(target, case.get("expected_text"), args.require_pdf_tools)
                    if result["exit_code"]:
                        errors.insert(0, f"AbX2T exit code {result['exit_code']}")
                    known = [issue for issue in manifest.get("known_content_issues", [])
                             if issue["case"] == case["id"] and issue["format"] == extension
                             and issue["message"] in errors]
                    allowed_messages = {issue["message"] for issue in known} if args.allow_known_content_issues else set()
                    blocking = [error for error in errors if error not in allowed_messages]
                    conversion = {"format": extension, "filename": target.name,
                                  "exists": target.is_file(), "run": result,
                                  "inspection": inspection, "errors": errors,
                                  "known_content_issues": known, "blocking_errors": blocking}
                    entry["conversions"].append(conversion)
                    entry["blocking_errors"].extend(f"{extension}: {error}" for error in blocking)
                    status = "FAIL" if blocking else "KNOWN CONTENT ISSUE" if errors else "OK"
                    print(f"  {extension}: {status}{': ' + '; '.join(errors) if errors else ''}", flush=True)
                if args.previews:
                    pdf = folder / (source.stem + "-converted.pdf")
                    entry["previews"] = previews(source, pdf, folder, args.max_preview_pages)
        except (OSError, ValueError, ET.ParseError, BadZipFile) as error:
            entry["errors"].append(str(error))
            entry["blocking_errors"].append(str(error))
            print(f"  FAIL: {error}", flush=True)
        entry["technical_pass"] = not entry["errors"] and all(not c["errors"] for c in entry["conversions"])
        failed += not entry["technical_pass"]
        blocking_failures += bool(entry["blocking_errors"])
        report["cases"].append(entry)
    report["failed_cases"] = failed
    report["blocking_failed_cases"] = blocking_failures
    report["allow_known_content_issues"] = args.allow_known_content_issues
    report["conversion_count"] = sum(len(c["conversions"]) for c in report["cases"])
    (output / "results/corpus.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_html(report, output)
    print(f"{len(cases)} cases, {report['conversion_count']} conversions, {failed} cases with alerts, {blocking_failures} blocking failures", flush=True)
    print(f"Visual review: {output / 'index.html'}", flush=True)
    return 1 if blocking_failures else 0


if __name__ == "__main__":
    sys.exit(main())
