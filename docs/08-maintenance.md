# 08 — Maintenance

## Monter de version ONLYOFFICE

C'est l'opération de maintenance principale. Tout part de [`VERSIONS`](../VERSIONS) :

1. **Bumper `VERSIONS`** : `ONLYOFFICE_VERSION` (tag DesktopEditors) et
   `ONLYOFFICE_CORE_BUILD` (tag core/sdkjs correspondant — visible dans les notes de
   release ONLYOFFICE). Vider les `SHA256_*`.
2. **Fetch** sur chaque plateforme : `build/fetch_onlyoffice_<os>` télécharge le nouvel
   artefact, affiche son SHA-256 → le recopier dans `VERSIONS` (épinglage).
   `--latest` permet de tester la dernière release sans éditer `VERSIONS`.
3. **core-master** : mettre le checkout au nouveau tag, rafraîchir les sources vendored
   (`zsh allfontsgen/build/scripts/sync_core.sh`) et recompiler allfontsgen sur les
   trois plateformes. Points à vérifier en premier si la compilation casse :
   - `ApplicationFontsWorker.cpp` (le patch thumbnail ne correspond plus) ;
   - erreurs FreeType → shims et define `FT_CONFIG_OPTIONS_H` ;
   - `build/config/common_sources.txt` / `common_defines.txt` (fichiers upstream
     ajoutés/renommés).
4. **Repackager et republier** : `build/package_<os>` puis `dotnet publish` (voir
   [04-build.md](04-build.md)).
5. **Valider** : `build/smoke_test.sh <exe publié>` sur chaque plateforme. Symptômes de
   régression classiques :
   - AllFonts.js généré mais x2t crashe → vérifier `DoctRenderer.config` et les chemins
     sdkjs (fichier JS ajouté/renommé upstream ? comparer avec la liste des scripts de
     sync) ;
   - sortie absente → vérifier `m_sAllFontsPath` / `m_sFontDir` dans le XML.
6. **Tagger** (voir ci-dessous). Les utilisateurs existants n'ont rien à faire : au
   premier lancement du nouvel exe, le marqueur `resources/.version` déclenche la
   ré-extraction automatique du nouveau bundle.

## Releases et tags

- Numérotation **alignée sur ONLYOFFICE** : le tag AbX2T reprend
  `ONLYOFFICE_CORE_BUILD` (ex. `v10.0.0.169`). Règle de lecture : si la version d'AbX2T
  est la dernière version ONLYOFFICE, on est à jour.
- Correctif du wrapper entre deux versions ONLYOFFICE : suffixer (`v10.0.0.169-2`) pour
  ne pas casser la correspondance.
- Publier avec chaque release les **SHA-256 des exécutables** (SmartScreen/Gatekeeper :
  binaires non signés, l'utilisateur doit pouvoir vérifier ce qu'il télécharge).

## Veille sécurité

x2t parse des fichiers potentiellement non fiables (PDF, formats legacy…) ; ONLYOFFICE
corrige régulièrement des vulnérabilités de parsing. Un bundle épinglé qui ne bouge
jamais accumule des CVE connues :

- vérifier régulièrement <https://github.com/ONLYOFFICE/DesktopEditors/releases>
  (`build/fetch_onlyoffice_<os> --latest` teste une nouvelle version en une commande) ;
- monter de version dès qu'une release corrige des failles de parsing.

## Entretien du dépôt

- `build/cache/` : téléchargements des releases ONLYOFFICE (gitignore). Supprimer un
  fichier force son re-téléchargement.
- Ne **jamais** committer `x2t/bin/`, `x2t/sdkjs/`, `src/assets.zip`, `core-master/`
  (tous gitignorés — reconstructibles).
- La documentation vit dans `docs/` uniquement ; chaque fichier se termine par le
  commit auquel il est à jour — le mettre à jour à chaque passe de doc.

## CI

`.github/workflows/build.yml` : un job par plateforme (windows/macos/ubuntu) qui
déroule le pipeline complet de [04-build.md](04-build.md) — fetch ONLYOFFICE
(téléchargement mis en cache, clé = hash de `VERSIONS`), packaging (compile
allfontsgen depuis les sources vendored si absent), publish NativeAOT, smoke test
sur l'exe publié, zip + SHA-256 en artefact. Déclenchée sur push main, PR, tag `v*`
et manuellement (`workflow_dispatch`). **Sur un tag `v*`, les artefacts des trois
plateformes sont attachés automatiquement à la GitHub release** — c'est le canal de
production des exécutables (l'AOT ne cross-compile pas).

## Chantiers futurs identifiés

- **Linux sans glibc (musl/Alpine)** : la voie réaliste est `gcompat` (shim glibc sur
  Alpine) — recompiler x2t en musl serait un chantier énorme, et le plancher glibc 2.34
  vient du runtime .NET lui-même.
- **Anglais** : passage du README/de la doc en anglais (ou bilingue) avant une audience
  internationale.
- **Signature de code** (ou distribution `winget`) pour éliminer SmartScreen/Gatekeeper.

---

*Documentation mise à jour pour ONLYOFFICE 10.0.0 (core 10.0.0.169).*
