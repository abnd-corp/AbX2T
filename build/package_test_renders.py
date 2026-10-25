#!/usr/bin/env python3
"""Archive release-specific test outputs; never add generated renders to Git."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

REPO = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=REPO / "dist/test-renders")
    parser.add_argument("--output", type=Path, default=REPO / "dist")
    parser.add_argument("--platform", required=True, choices=["macos-arm64", "windows-x86_64", "linux-x86_64"])
    args = parser.parse_args()
    folder = args.input.resolve()
    versions = dict(line.split("=", 1) for line in (REPO / "VERSIONS").read_text().splitlines()
                    if line and not line.startswith("#"))
    for path in ("corpus/results.json", "fonts/results.json", "cli/results.json"):
        if not (folder / path).is_file():
            parser.error(f"Missing test results: {path}")
    corpus = json.loads((folder / "corpus/results.json").read_text(encoding="utf-8"))
    fonts = json.loads((folder / "fonts/results.json").read_text(encoding="utf-8"))
    cli = json.loads((folder / "cli/results.json").read_text(encoding="utf-8"))
    if corpus["blocking_failed_cases"] or not fonts["passed"] or not cli["passed"]:
        parser.error("Tests contain blocking failures; do not package them as validated release renders")
    fixture_root = REPO / "build/testdata/corpus"
    shutil.copyfile(fixture_root / "ATTRIBUTIONS.md", folder / "ATTRIBUTIONS.md")
    shutil.copytree(fixture_root / "licenses", folder / "licenses", dirs_exist_ok=True)
    shutil.copytree(fixture_root / "fonts", folder / "font-licenses", dirs_exist_ok=True)
    provenance = {
        "onlyoffice_version": versions["ONLYOFFICE_VERSION"],
        "core_build": versions["ONLYOFFICE_CORE_BUILD"],
        "platform": args.platform,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "known_content_issues": [issue for case in corpus["cases"]
                                 for conversion in case["conversions"]
                                 for issue in conversion.get("known_content_issues", [])],
        "visual_review": "User compares the original DOCX/DOC directly to the produced PDF; no reference PDF.",
    }
    (folder / "TEST-RUN.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (folder / "index.html").write_text('''<!doctype html><html lang="fr"><meta charset="utf-8">
<title>AbX2T — rendus des tests</title><style>body{font:17px/1.6 system-ui;max-width:950px;margin:40px auto;padding:20px}a{color:#155ca1}</style>
<h1>Originaux et rendus de cette version</h1>
<p>Comparer les fichiers originaux directement aux PDF produits. Aucun PDF de référence n’a été créé ; la fidélité visuelle reste à contrôler par l’utilisateur.</p>
<ul><li><a href="corpus/index.html">18 documents du corpus : originaux et 38 conversions</a></li>
<li><a href="fonts/fugaz-one.docx">Original du test Fugaz One</a> —
<a href="fonts/01-missing-font.pdf">PDF sans la police</a> —
<a href="fonts/02-manually-added-font.pdf">PDF après ajout manuel</a> —
<a href="fonts/results.json">Résultats des deux scénarios</a></li>
<li><a href="cli/results.json">Résultats CLI, batch et scripts</a></li>
<li><a href="ATTRIBUTIONS.md">Attributions et licences</a> — <a href="TEST-RUN.json">Version, plateforme, commit et alertes connues</a></li></ul>
<p>Les éventuelles alertes de contenu connues sont conservées dans les résultats ; une conversion exécutée avec succès n’est pas une validation visuelle.</p></html>''', encoding="utf-8")
    args.output.mkdir(parents=True, exist_ok=True)
    name = f"Abx2t-test-renders-v{versions['ONLYOFFICE_CORE_BUILD']}-{args.platform}.zip"
    archive = args.output / name
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zipped:
        for file in sorted(folder.rglob("*")):
            if file.is_file():
                zipped.write(file, file.relative_to(folder))
    with ZipFile(archive) as zipped:
        if zipped.testzip():
            raise ValueError("Invalid render archive")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(name + ".sha256").write_text(f"{digest}  {name}\n", encoding="utf-8")
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
