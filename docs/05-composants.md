# 05 — Composants

## VERSIONS

[`VERSIONS`](../VERSIONS), à la racine, est la **source unique de vérité** des versions.
Tous les composants ONLYOFFICE du dépôt s'alignent dessus, ainsi que les tags de release
d'AbX2T lui-même :

| Clé | Rôle |
|---|---|
| `ONLYOFFICE_VERSION` | Tag de la release DesktopEditors (3 composants, ex. `10.0.0`) — construit les URL de téléchargement |
| `ONLYOFFICE_CORE_BUILD` | Build core/sdkjs correspondant (4 composants, ex. `10.0.0.169`) — version affichée par `--version`/`--license`, pointeur source AGPL, marqueur `resources/.version` |
| `SHA256_*` | Empreintes des artefacts officiels, vérifiées par les scripts fetch (vides = affichées au lieu d'être vérifiées, pour amorcer une nouvelle version) |

Le fichier est parsé par MSBuild (`src/Abx2t.csproj`) et par les scripts fetch : garder
le format `CLE=valeur` et **pas d'apostrophes dans les commentaires**.

## Abx2t (`src/`)

Le produit : un programme C# d'un seul fichier (`Program.cs`), publié en NativeAOT.
Aucune dépendance NuGet. Il embarque `assets.zip` (ressource) et orchestre tout le
reste — voir [03-architecture.md](03-architecture.md).

## x2t + sdkjs (`x2t/`)

Le moteur de conversion ONLYOFFICE, **jamais recompilé ni modifié ici** : binaires
précompilés issus des releases officielles, simplement emballés et invoqués en
sous-processus.

```
x2t/
├── bin/<os-arch>/    x2t + DLLs (Windows) / frameworks (macOS) / .so + icudtl*.dat (Linux)
│                     + DoctRenderer.config — peuplé par les scripts de sync
├── sdkjs/            Runtime JS minimal nécessaire à la conversion
└── build/scripts/    sync_from_release_macos.sh, sync_from_release_linux.sh,
                      sync_from_install_windows.ps1, convert.sh
```

`bin/` et `sdkjs/` ne sont **pas versionnés** (gitignore) : `build/fetch_onlyoffice_<os>`
les reconstitue à l'identique depuis la release GitHub `ONLYOFFICE/DesktopEditors`
épinglée par `VERSIONS` (ou `--latest`), hash vérifié, puis enchaîne sur le script de
sync. Les scripts de sync restent utilisables seuls (fallback manuel, voir
[04-build.md](04-build.md#fallback-manuel-sans-les-scripts-fetch)).

**sdkjs minimal** : les scripts de sync ne copient que les fichiers requis par la
conversion — `common/Native/*`, `common/libfont/engine/fonts_native.js`,
`{word,slide,cell,visio}/sdk-all-min.js` **et** `sdk-all.js` (requis ensemble),
`pdf/src/engine/{drawingfile_native.js,cmap.bin}`, `vendor/xregexp/`. La présence de
chacun est vérifiée avant d'écrire.

**`convert.sh`** (macOS/Linux) : point d'entrée pour tester le moteur seul sans passer
par Abx2t — gère le XML de config et garantit le nettoyage du dossier temporaire que
x2t peut laisser derrière lui (voir [03-architecture.md](03-architecture.md)).

## allfontsgen (`allfontsgen/`)

Générateur de l'index de polices (`AllFonts.js`, `font_selection.bin`), compilé ici —
contrairement à x2t — depuis un sous-ensemble des sources ONLYOFFICE/core.

```
allfontsgen/
├── src/              Sources upstream copiées depuis core-master — JAMAIS modifiées
├── build/config/     Manifestes : listes de sources, includes, defines, libs par plateforme
├── build/scripts/    build_<os>, generate_<os>, prepare_generated_sources.sh, sync_core.sh
├── build/shims/      Overrides injectés à la compilation sans toucher src/
├── build/generated/  Overlay généré au build (gitignore)
└── output/<os-arch>/fonts/   AllFonts.js généré (gitignore)
```

### Invariants

- **Ne jamais patcher `src/`** : toute adaptation locale vit dans `build/shims/`,
  `build/scripts/` ou `build/generated/`.
- Les dépendances thumbnail (raster/graphics) sont désactivées en patchant
  `ApplicationFontsWorker.cpp` **à la volée** dans `build/generated/`
  (`prepare_generated_sources.sh` sur macOS/Linux, inline dans `build_windows.ps1`).
- Shims clés : `posix_compat.h` (headers POSIX, force-include partout),
  `freetype_ftoption.h` (zlib FreeType désactivé, macOS/Linux),
  `allfontsgen_ftoptions.h` (idem Windows, via le define `FT_CONFIG_OPTIONS_H`).
- `allfontsgen/src/` est une copie statique : après une montée de version de
  core-master, la rafraîchir avec `zsh allfontsgen/build/scripts/sync_core.sh` puis
  recompiler et retester sur les trois plateformes.

Build et génération validés sur les trois plateformes ; la conversion x2t de bout en
bout est validée sur les trois aussi (le smoke test la rejoue).

## core-master (`core-master/`)

Checkout des sources <https://github.com/ONLYOFFICE/core>, **au tag
`ONLYOFFICE_CORE_BUILD` de `VERSIONS`** (considéré à la même version que le reste du
bundle). Non versionné ici. Requis uniquement pour (re)compiler allfontsgen ; inutile
pour utiliser ou packager Abx2t si `allfontsgen/build/bin/` existe déjà.

---

*Documentation mise à jour pour ONLYOFFICE 10.0.0 (core 10.0.0.169).*
