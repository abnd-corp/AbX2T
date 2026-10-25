# Third-party notices

AbX2T (Copyright (C) 2026 Hugo Lagouardat, [Abend-core](https://github.com/Abend-core) project)
is distributed under the [GNU AGPLv3](LICENSE) license. This file documents the third-party
components bundled in this repository, their licenses, and where to find their corresponding
source code, in accordance with AGPLv3 obligations (section 6, "Corresponding Source").

## ONLYOFFICE (x2t, sdkjs)

- **Publisher**: Ascensio System SIA — <https://www.onlyoffice.com>
- **Copyright**: (C) Ascensio System SIA.
- **License**: [GNU AGPLv3](https://github.com/ONLYOFFICE/core/blob/master/LICENSE) (same
  license as this repository)
- **Bundled components**:
  - `x2t/bin/windows-x86_64/`: the `x2t.exe` binary and its DLLs (conversion engine), version
    **10.0.0.169** (read from the binary's own metadata). Bundled format converters (DjVuFile,
    HwpFile, OFDFile, IWork, StarMath2OOXML, XpsFile, etc.): all present in ONLYOFFICE/core's
    public source tree — no proprietary or undocumented "black box" component.
  - `x2t/bin/macos-arm64/`: the same `x2t` binary and its `.framework` bundles, macOS build of
    the same conversion engine, sourced from an official ONLYOFFICE Desktop Editors release.
  - `x2t/bin/linux-x86_64/`: the same `x2t` binary, its `.so` libraries and ICU data files,
    Linux build of the same conversion engine, sourced from the official ONLYOFFICE Desktop
    Editors Debian package (`onlyoffice-desktopeditors_10.0.0_amd64.deb`, from
    <https://github.com/ONLYOFFICE/DesktopEditors/releases/tag/v10.0.0>).
  - `x2t/sdkjs/`: JavaScript runtime (word/cell/slide/visio/pdf/common) of the same SDK.
    `x2t/sdkjs/common/AllFonts.js` is not upstream code: it is a font index generated locally
    on each machine by `allfontsgen`.
- **Provenance**: components are taken as-is from an official ONLYOFFICE Desktop Editors
  installation or release package (see `x2t/build/scripts/sync_from_install_windows.ps1`,
  `sync_from_release_macos.sh` and `sync_from_release_linux.sh`). **No modification** is made to these binaries or JS files: AbX2T
  only packages them and invokes them as a subprocess from its own code
  (`src/Program.cs`).
- **Corresponding source** (exact version match): ONLYOFFICE publishes the source for this
  exact version under AGPLv3, tagged `v10.0.0.169`:
  - <https://github.com/ONLYOFFICE/core/releases/tag/v10.0.0.169>
  - <https://github.com/ONLYOFFICE/sdkjs/releases/tag/v10.0.0.169>
  - Desktop application shell (not bundled here, for reference):
    <https://github.com/ONLYOFFICE/DesktopEditors>

  AbX2T does not republish this source code (already public and maintained by ONLYOFFICE);
  should it become unavailable, contact this repository's maintainer (see README) for a copy.
- **Third-party libraries inside the ONLYOFFICE binaries**: the x2t binaries statically embed
  several libraries under their own (permissive or weak-copyleft) licenses, as documented
  upstream in [ONLYOFFICE/core `3DPARTY.md`](https://github.com/ONLYOFFICE/core/blob/master/3DPARTY.md)
  — notably ICU (`icudt74.dll`, `icuuc74.dll`; Unicode License v3), FreeType (FTL), HarfBuzz
  (MIT), Boost (BSL), V8 (BSD-3-Clause), hunspell/hyphen (MPL), OpenSSL (Apache-2.0), and
  others. See that file for the complete list and license texts. `x2t/sdkjs/vendor/` also
  contains [XRegExp](https://github.com/slevithan/xregexp) (MIT, Copyright (C) Steven
  Levithan).

## ONLYOFFICE/core source subset (allfontsgen)

- **Publisher**: Ascensio System SIA — <https://www.onlyoffice.com>
- **License**: [GNU AGPLv3](https://github.com/ONLYOFFICE/core/blob/master/LICENSE) (same
  license as this repository)
- **What's bundled**: `allfontsgen/src/` is a vendored copy of a subset of the
  [ONLYOFFICE/core](https://github.com/ONLYOFFICE/core) source tree (`Common/`,
  `DesktopEditor/`, `OdfFile/`, `UnicodeConverter/`), copied in verbatim by
  `allfontsgen/build/scripts/sync_core.sh`. It is compiled locally into `allfontsgen`, a
  small tool used to index system fonts into `AllFonts.js`. Unlike x2t/sdkjs above, this
  source is committed directly in this repository (not just referenced), which is the
  simplest way to guarantee the Corresponding Source travels with the binary built from it.
- **Source version**: the vendored subset follows tag `v10.0.0.169`, commit
  `76af764fcb777291098c73728044249b6893af6a`. It includes the upstream
  `DesktopEditor/graphics/pro/MemoryStorage.h` header required by this version.
- **Modification**: at build time, `allfontsgen/build/scripts/prepare_generated_sources.sh`
  (macOS/Linux) and `build_windows.ps1` (Windows, inline) apply a small patch to one file,
  `DesktopEditor/fontengine/ApplicationFontsWorker.cpp`: they wrap the `SaveThumbnails`
  function body and its raster/graphics includes behind an
  `ALLFONTSGEN_DISABLE_THUMBNAILS` preprocessor guard, so `allfontsgen` can build without
  pulling in thumbnail-rendering dependencies it doesn't need. The patch is applied to a
  generated copy under `allfontsgen/build/generated/` (not committed); the vendored copy
  under `allfontsgen/src/` stays untouched. The exact patch is fully visible and
  reproducible by reading those two scripts — no hidden or undocumented change.
- **FreeType**: the vendored subset includes FreeType 2.10.4
  (`allfontsgen/src/DesktopEditor/freetype-2.10.4/`), which is compiled into
  `allfontsgen` and used under the
  [FreeType License (FTL)](https://gitlab.freedesktop.org/freetype/freetype/-/blob/master/docs/FTL.TXT).
  As required by the FTL: *Portions of this software are copyright © The FreeType Project
  (<https://www.freetype.org>). All rights reserved.*
- **Corresponding source**: the unmodified upstream version of every file, including
  `ApplicationFontsWorker.cpp`, is available at <https://github.com/ONLYOFFICE/core>.

## Trademarks

"ONLYOFFICE" and "Ascensio System SIA" are trademarks of their respective owners. AbX2T is not
affiliated with, endorsed by, or sponsored by Ascensio System SIA. The name "AbX2T" does not
use the ONLYOFFICE trademark as its primary identifier; references to ONLYOFFICE in this
repository are purely descriptive (indicating that this project invokes and packages their
components).

## AbX2T original code

Everything else in this repository (the `Abx2t.exe` C# code, sync/build scripts,
documentation) — i.e. everything outside `allfontsgen/src/`, `x2t/bin/`, and `x2t/sdkjs/` —
is original work by Hugo Lagouardat (Abend-core), published under the
same AGPLv3 license — see [LICENSE](LICENSE).
