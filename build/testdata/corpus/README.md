# Bibliothèque de conversion

Ce dossier versionne **18 originaux téléchargés** : 10 DOCX, 4 DOC, 2 fichiers
Excel, 1 ODS et 1 PPTX. Un dix-neuvième document créé pour AbX2T sert aux deux
scénarios de police. Les originaux sont conservés sans modification.

```text
corpus/
  ATTRIBUTIONS.md          sources, auteurs et licences, dont la police
  manifest.json            révisions, chemins, tailles, SHA-256, alertes connues
  originals/apache-poi/    originaux Apache POI
  originals/libreoffice/   originaux LibreOffice
  originals/abx2t/         document reproductible demandant Fugaz One
  fonts/fugaz-one/         TTF original, OFL.txt et métadonnées upstream
  licenses/               textes complets des licences et notices
```

Les licences respectives sont détaillées dans [ATTRIBUTIONS.md](ATTRIBUTIONS.md).
Le contenu Wikipédia du DOCX arabe a sa propre attribution CC BY-SA. Les polices
propriétaires nommées par certains documents (Aptos, etc.) ne sont pas fournies.
Les sorties restent dans `dist/`, hors Git. Les tests vérifient les originaux
committés par SHA-256 et ne téléchargent aucun document en CI.

## Corpus

```sh
python3 build/corpus_test.py --exe chemin/vers/Abx2t --offline --output dist/corpus-nouveau
```

38 conversions couvrent PDF, TXT, ODT, XLSX, ODS, CSV et ODP selon l'entrée.
`--case word-shapes` sélectionne un seul document. Utiliser un dossier de sortie
neuf pour qu'un ancien rendu ne passe jamais pour un résultat neuf.

Cas couverts : tableaux/cellules fusionnées, listes imbriquées, en-têtes/pieds de
page, colonnes, images flottantes/vectorielles, zones de texte, formes, arabe/latin,
polices explicites, pagination, graphiques et formats numériques. La priorité reste
DOCX/DOC → PDF. L'utilisateur compare directement **l'original et le PDF produit**.
Aucun PDF de référence ni conversion LibreOffice n'est créé. Les aperçus
facultatifs `--previews` sont indicatifs, sans verdict visuel.

## Police absente puis ajoutée

```sh
python3 build/font_test.py --exe chemin/vers/Abx2t --output dist/font-tests
```

1. Fugaz One absente : conversion sans erreur, absence de la police dans l'index,
   présence d'une police de substitution dans les dictionnaires du PDF.
2. Copier le TTF dans `custom-fonts/` du même exécutable, puis reconvertir : le PDF
   doit utiliser et embarquer Fugaz One, et l'index/manifeste doit s'actualiser.

Le test ne supprime pas le cache, n'installe pas la police dans le système et ne
modifie pas le mécanisme de substitution. Il échoue si la police est déjà présente
au premier scénario. Il vérifie la police utilisée dans le PDF, pas sa seule taille.

L'ajout manuel existant peut se faire en ligne de commande :

```sh
mkdir -p /dossier/de/Abx2t/custom-fonts
cp build/testdata/corpus/fonts/fugaz-one/FugazOne-Regular.ttf /dossier/de/Abx2t/custom-fonts/
/dossier/de/Abx2t/Abx2t document.docx document.pdf
```

Cette version n'expose pas d'option `--font` dans l'aide du wrapper. Le mécanisme
`custom-fonts/` est conservé. Le DOCX se régénère à l'identique avec
`python3 build/font_test.py --write-fixture`. La licence OFL autorise la
redistribution du TTF inchangé avec sa notice de copyright et son texte de licence.

## CLI, batch et scripts

```sh
python3 build/cli_test.py --exe chemin/vers/Abx2t --test-timeout --output dist/cli-tests
```

Aide/version/licence et alias, erreurs d'options/formats, chemins avec espaces et
accents, casse, verbeux, timeout désactivé, batch séquentiel/parallèle, jokers,
limites de `--jobs`, collisions, échec partiel, codes d'erreur et sortie manquante
sont exercés. Sur Unix, `--test-timeout` vérifie réellement le délai d'une minute
et l'arrêt du sous-processus. Bash/Zsh analysent leurs scripts ; les entrées d'aide
et d'erreur des fetchers sont exercées. PowerShell est analysé si `pwsh` est présent.
Les outils absents sont consignés. Ces tests ne simulent pas de partage UNC/SMB
réel ni le repli du répertoire inscriptible sur tous les systèmes.

## Alertes techniques connues

Le corpus garde toutes les sorties et diagnostics. Les vérifications portent sur
l'exécution, les structures Office/PDF et certains fragments de texte. Poppler,
si disponible, relève aussi pages, texte et polices ; `--require-pdf-tools` le rend
obligatoire (job Linux). Ces vérifications ne valident pas la fidélité visuelle.

- [#16](https://github.com/abnd-corp/AbX2T/issues/16) : fragment arabe non retrouvé
  dans l'extraction du PDF sur macOS.
- [#17](https://github.com/abnd-corp/AbX2T/issues/17) : le TXT du document constitué
  de zones de texte ne contient que le BOM.

Par défaut, ces alertes font échouer le script. La CI passe explicitement
`--allow-known-content-issues` : seules les deux signatures exactes du manifeste
sont admises et restent signalées dans les JSON/rapports. Tout nouvel échec bloque
le pipeline. Les tests de police et CLI n'ont aucune exception de ce type.

## Rendus des versions

La CI exécute le corpus, les deux scénarios de police et les tests CLI sur Windows,
macOS et Linux. Les sorties/diagnostics des essais, même échoués, sont disponibles
en artefacts CI. Après réussite des contrôles bloquants, elle assemble
`Abx2t-test-renders-v<core>-<plateforme>.zip` et son SHA-256 avec originaux, sorties,
attributions, licences et index. La version, la plateforme, le commit et les
alertes connues sont inscrits dans l'archive.

Un tag `v*` attache ces archives à la release avec les exécutables. Aucun rendu
n'est committé et aucune release n'est créée par un test de PR.
