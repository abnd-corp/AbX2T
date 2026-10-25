#!/usr/bin/env python3
"""Package the single testdata tree as the release example, without duplicating it."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from corpus_test import report_html

REPO = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=REPO / 'testdata')
    parser.add_argument('--output', type=Path, default=REPO / 'dist')
    parser.add_argument('--platform', required=True, choices=['macos-arm64', 'windows-x86_64', 'linux-x86_64'])
    args = parser.parse_args()
    folder = args.input.resolve()
    versions = dict(line.split('=', 1) for line in (REPO / 'VERSIONS').read_text().splitlines()
                    if line and not line.startswith('#'))
    for path in ('results/corpus.json', 'results/fonts.json', 'results/cli.json'):
        if not (folder / path).is_file():
            parser.error(f'Missing test results: {path}')
    corpus = json.loads((folder / 'results/corpus.json').read_text(encoding='utf-8'))
    fonts = json.loads((folder / 'results/fonts.json').read_text(encoding='utf-8'))
    cli = json.loads((folder / 'results/cli.json').read_text(encoding='utf-8'))
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if {case['id'] for case in corpus['cases']} != {case['id'] for case in manifest['cases']}:
        parser.error('Run the complete corpus before packaging release examples')
    if corpus['blocking_failed_cases'] or not fonts['passed'] or not cli['passed']:
        parser.error('Blocking test failures: do not package as validated release examples')
    if fonts['font']['document_sha256'] != manifest['font_fixture']['document_sha256']:
        parser.error('Font results do not match the current source fixture')
    for case in manifest['cases']:
        source = folder / case['path']
        if hashlib.sha256(source.read_bytes()).hexdigest() != case['sha256']:
            parser.error(f'Source checksum mismatch: {case["id"]}')
    provenance = {
        'onlyoffice_version': versions['ONLYOFFICE_VERSION'],
        'core_build': versions['ONLYOFFICE_CORE_BUILD'],
        'platform': args.platform,
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
        'working_tree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=REPO, text=True).strip()),
        'known_content_issues': [issue for case in corpus['cases'] for conversion in case['conversions']
                                 for issue in conversion.get('known_content_issues', [])],
        'visual_review': 'Compare original/ directly with converted/; no reference PDF.',
    }
    (folder / 'TEST-RUN.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report_html(corpus, folder)
    args.output.mkdir(parents=True, exist_ok=True)
    name = f'Abx2t-testdata-v{versions["ONLYOFFICE_CORE_BUILD"]}-{args.platform}.zip'
    archive = args.output / name
    with ZipFile(archive, 'w', compression=ZIP_DEFLATED) as zipped:
        for file in sorted(folder.rglob('*')):
            if file.is_file():
                zipped.write(file, Path('testdata') / file.relative_to(folder))
    with ZipFile(archive) as zipped:
        if zipped.testzip():
            raise ValueError('Invalid testdata archive')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(name + '.sha256').write_text(f'{digest}  {name}\n', encoding='utf-8')
    print(archive)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
