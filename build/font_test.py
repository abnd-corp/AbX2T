#!/usr/bin/env python3
"""Test missing-font fallback and manual custom-font loading, without changing AbX2T."""

import argparse
import hashlib
import io
import json
import re
import shutil
import tempfile
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from corpus_test import MANIFEST, REPO, run


def fixture_bytes():
    """A deterministic, original DOCX using the freely redistributable Fugaz One font."""
    from xml.sax.saxutils import escape
    paragraphs = []
    for size, text in [
        (44, "Fugaz One : police absente puis ajoutée"),
        (28, "AbX2T font probe: missing font fallback and custom font loading."),
        (28, "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz 0123456789"),
        (28, "Accents : été, Noël, façade. Ponctuation : ! ? & ( )"),
    ]:
        paragraphs.append(f'<w:p><w:r><w:rPr><w:rFonts w:ascii="Fugaz One" '
                          f'w:hAnsi="Fugaz One" w:cs="Fugaz One"/><w:sz w:val="{size}"/>'
                          f'</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>')
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '</Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>',
        "word/document.xml": '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
        + "".join(paragraphs) + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/>'
        '</w:sectPr></w:body></w:document>',
    }
    buffer = io.BytesIO()
    # Fixed ZIP metadata and no compression make the committed bytes identical
    # across Windows/Unix and different Python/zlib versions.
    with ZipFile(buffer, "w", compression=ZIP_STORED) as archive:
        for name, contents in files.items():
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o600 << 16
            info.compress_type = ZIP_STORED
            archive.writestr(info, contents.encode("utf-8"))
    return buffer.getvalue()


def pdf_fonts(pdf):
    data = pdf.read_bytes()
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
        raise ValueError("Invalid PDF")
    # ONLYOFFICE's generated PDFs expose font dictionaries directly. Fail closed
    # if a future PDF writer changes that representation; never infer font usage
    # merely from a successful process exit or from differences between file sizes.
    names = sorted({name.decode("ascii") for name in
                    re.findall(rb"/BaseFont\s*/([^\s/<>\[\]()]+)", data)})
    if not names:
        raise ValueError("No readable PDF font dictionary; update the font inspector")
    return names


def is_fugaz(name):
    return "fugazone" in re.sub(r"[^a-z]", "", name.lower())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--output", type=Path, default=REPO / "dist/font-tests")
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args()
    root = MANIFEST.parent
    source = root / "originals/abx2t/fugaz-one.docx"
    if args.write_fixture:
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(fixture_bytes())
        print(source)
        return 0
    if not args.exe or not args.exe.is_file():
        parser.error("--exe must point to a published AbX2T executable")
    if source.read_bytes() != fixture_bytes():
        parser.error("The committed font DOCX differs from its reproducible source")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fixture = manifest["font_fixture"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != fixture["document_sha256"]:
        parser.error("Font document checksum mismatch")
    font = root / fixture["font_path"]
    if hashlib.sha256(font.read_bytes()).hexdigest() != fixture["font_sha256"]:
        parser.error("Font checksum mismatch")
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("Use an empty output directory")
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, output / source.name)
    shutil.copyfile(root / fixture["license_path"], output / "Fugaz-One-OFL.txt")
    report = {"font": fixture, "cases": [], "production_code_modified": False}
    with tempfile.TemporaryDirectory(prefix="abx2t_font_") as temporary:
        runtime = Path(temporary)
        exe = runtime / ("Abx2t.exe" if args.exe.suffix.lower() == ".exe" else "Abx2t")
        shutil.copy2(args.exe.resolve(), exe)
        for name, added in (("01-missing-font", False), ("02-manually-added-font", True)):
            case = {"id": name, "errors": []}
            try:
                index = runtime / "allfonts/AllFonts.js"
                state = runtime / "allfonts/fonts.manifest"
                before = state.read_bytes() if state.exists() else None
                if added:
                    # This is the existing manual CLI operation: copy a font into
                    # custom-fonts/. Do NOT delete/regenerate caches in the test.
                    custom = runtime / "custom-fonts"
                    custom.mkdir(exist_ok=True)
                    shutil.copyfile(font, custom / font.name)
                pdf = output / (name + ".pdf")
                result = run([str(exe), "--timeout", "2", str(source), str(pdf)])
                case["run"] = result
                if result["exit_code"] != 0:
                    raise ValueError(f"Conversion did not succeed: exit {result['exit_code']}")
                families = pdf_fonts(pdf)
                case["pdf_fonts"] = families
                case["font_in_index"] = "Fugaz One" in index.read_text(encoding="utf-8-sig")
                case["manifest_sha256"] = hashlib.sha256(state.read_bytes()).hexdigest()
                uses_font = any(is_fugaz(family) for family in families)
                if uses_font != added or case["font_in_index"] != added:
                    raise ValueError("Font availability/index/PDF usage does not match the scenario")
                if added and (before is None or before == state.read_bytes()):
                    raise ValueError("The cached font manifest did not refresh after manual addition")
                if added and not re.search(rb"/FontFile[23]?\s+\d+\s+\d+\s+R", pdf.read_bytes()):
                    raise ValueError("Custom font was named but no embedded font program was found")
                case["passed"] = True
                print(f"{name}: OK; PDF fonts: {', '.join(families)}", flush=True)
            except (OSError, ValueError) as error:
                case["passed"] = False
                case["errors"].append(str(error))
                print(f"{name}: FAIL: {error}", flush=True)
            report["cases"].append(case)
    report["passed"] = all(case["passed"] for case in report["cases"])
    (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
