# AbX2T

[English](README.md) · Français

Convertisseur de documents en ligne de commande, autonome, en **un seul exécutable** —
basé sur le moteur de conversion ONLYOFFICE (x2t). Windows x86_64, macOS arm64,
Linux x86_64 (y compris conteneurs distroless).

```
Abx2t rapport.docx rapport.pdf
```

Aucune installation : au premier lancement, l'exécutable extrait ses composants et
indexe les polices de la machine tout seul. Entrée : tout ce qu'ONLYOFFICE sait lire
(docx, doc, odt, xlsx, pptx, pdf, html, rtf, epub, vsdx…). Sortie : docx, odt, rtf,
txt, html, pdf, pptx, odp, xlsx, ods, csv, xps. Les chemins réseau
(`\\serveur\partage`) sont gérés.

## Documentation

**Tout est dans [docs/](docs/README.md)** — utilisation détaillée, architecture, build,
composants, performances, licences, maintenance.

- Utilisateur : [docs/02-utilisation.md](docs/02-utilisation.md)
- Développeur/mainteneur : [docs/01-vue-ensemble.md](docs/01-vue-ensemble.md) puis
  [docs/04-build.md](docs/04-build.md)

## Construire depuis les sources (résumé)

```sh
# macOS (même pipeline sur Windows/Linux, voir docs/04-build.md)
zsh build/fetch_onlyoffice_macos.sh                      # binaires ONLYOFFICE officiels (hash vérifié)
cd allfontsgen && zsh build/scripts/build_macos.sh && zsh build/scripts/generate_macos.sh && cd ..
cp allfontsgen/output/macos-arm64/fonts/AllFonts.js x2t/sdkjs/common/AllFonts.js
zsh build/package_macos.sh
dotnet publish src/Abx2t.csproj -c Release -r osx-arm64
bash build/smoke_test.sh src/bin/Release/net10.0/osx-arm64/publish/Abx2t
```

Les versions du bundle ONLYOFFICE sont épinglées dans [`VERSIONS`](VERSIONS) (source
unique). Les binaires ONLYOFFICE ne sont pas commités : ils se retéléchargent à
l'identique depuis les releases officielles.

## Licence et attribution

AbX2T est distribué sous **[GNU AGPLv3](LICENSE)**.
Copyright (C) 2026 Hugo Lagouardat, projet [Abnd](https://github.com/abnd-corp).

Ce projet emballe des composants **ONLYOFFICE** (x2t, sdkjs, sous-ensemble de sources
pour allfontsgen), Copyright (C) Ascensio System SIA, également AGPLv3, ainsi que
FreeType (FTL) — utilisés non modifiés. Détails, versions et sources correspondantes :
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) et
[docs/07-licences.md](docs/07-licences.md). `Abx2t --license` affiche le même résumé.

AbX2T n'est ni affilié à, ni approuvé, ni sponsorisé par Ascensio System SIA /
ONLYOFFICE.

---

*Documentation à jour au commit `1fe36b8`.*
