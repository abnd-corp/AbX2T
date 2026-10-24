# AbX2T

English · [Français](README.fr.md)

Standalone command-line document converter shipped as **a single executable**, built on
the ONLYOFFICE conversion engine (x2t). Windows x86_64, macOS arm64, Linux x86_64
(including distroless containers).

```
Abx2t report.docx report.pdf
```

Nothing to install: on first run, the executable extracts its components and indexes the
machine's fonts by itself. Input: anything ONLYOFFICE can read (docx, doc, odt, xlsx,
pptx, pdf, html, rtf, epub, vsdx…). Output: docx, odt, rtf, txt, html, pdf, pptx, odp,
xlsx, ods, csv, xps. Network paths (`\\server\share`) are supported.

## Usage

```
Abx2t [options] <source> <output>
Abx2t [options] --to <ext> <sources...> <output_dir>
```

```sh
Abx2t workbook.xlsx data.csv
Abx2t --to pdf *.docx out/                         # batch, in parallel
Abx2t --to pdf --jobs 4 report.docx sheet.xlsx out/
```

| Option | Effect |
|---|---|
| `--to <ext>` | Batch mode: output format, each source keeps its own name in the target folder |
| `--jobs <n>` | Batch mode: parallel conversions (default: 2 to 4 depending on the CPU) |
| `--timeout <minutes>` | Maximum duration per file (default: 30, `0` = unlimited) |
| `--verbose` | Show x2t output even when the conversion succeeds |
| `--version` | AbX2T and bundled ONLYOFFICE versions |
| `--license` | AGPLv3 licence and ONLYOFFICE attribution |
| `--help` | Full help |

Exit codes: `0` success, `1` usage or wrapper error, `2` x2t engine error, `3` timeout.

The executable is not code-signed: check the SHA-256 published with the release before
bypassing Windows SmartScreen or macOS Gatekeeper.

## Documentation

The detailed documentation is in French, in [docs/](docs/README.md): usage, architecture,
build, components, performance, licences, maintenance.

## Building from source (summary)

```sh
# macOS (same pipeline on Windows/Linux, see docs/04-build.md)
zsh build/fetch_onlyoffice_macos.sh                      # official ONLYOFFICE binaries (hash checked)
cd allfontsgen && zsh build/scripts/build_macos.sh && zsh build/scripts/generate_macos.sh && cd ..
cp allfontsgen/output/macos-arm64/fonts/AllFonts.js x2t/sdkjs/common/AllFonts.js
zsh build/package_macos.sh
dotnet publish src/Abx2t.csproj -c Release -r osx-arm64
bash build/smoke_test.sh src/bin/Release/net10.0/osx-arm64/publish/Abx2t
```

ONLYOFFICE bundle versions are pinned in [`VERSIONS`](VERSIONS) (single source of truth).
ONLYOFFICE binaries are not committed: they are downloaded again, identically, from the
official releases.

## Licence and attribution

AbX2T is distributed under the **[GNU AGPLv3](LICENSE)**.
Copyright (C) 2026 Hugo Lagouardat, [Abnd](https://github.com/abnd-corp) project.

This project bundles **ONLYOFFICE** components (x2t, sdkjs, a subset of sources for
allfontsgen), Copyright (C) Ascensio System SIA, also AGPLv3, as well as FreeType (FTL),
all used unmodified. Details, versions and corresponding sources:
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) and
[docs/07-licences.md](docs/07-licences.md). `Abx2t --license` prints the same summary.

AbX2T is not affiliated with, endorsed or sponsored by Ascensio System SIA / ONLYOFFICE.
