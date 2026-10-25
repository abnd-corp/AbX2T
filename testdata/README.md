# Testdata — originaux et conversions

C'est le **seul jeu de données** utilisé en local et fourni comme exemple avec les
releases. On compare directement `original/` à `converted/`, sans PDF de référence.

```text
testdata/
  original/
    apache-poi/       16 documents téléchargés, conservés sans modification
    libreoffice/      2 DOCX téléchargés, conservés sans modification
    abx2t/            smoke test et original du test Fugaz One
  converted/
    word-*/           conversions des DOCX
    legacy-*/         conversions des DOC historiques
    sheets-*/         conversions des tableurs
    slides/           conversions de la présentation
    fonts/
      01-missing-font.pdf
      02-manually-added-font.pdf
  fonts/fugaz-one/     TTF original, OFL.txt et métadonnées de la police
  licenses/           textes complets des licences et notices
  ATTRIBUTIONS.md     auteurs, origines et droits de redistribution
  manifest.json       chemins, révisions et empreintes des originaux
  results/            rapports techniques des tests
  index.html          liens vers les originaux et les fichiers convertis
```

`original/` et `converted/` sont destinés à être versionnés ensemble pour servir
de comparaison et de démonstration, avec `fonts/`, `licenses/`, le manifeste et
cette documentation. Seuls `results/` et les index/provenances générés restent hors
Git. Une nouvelle exécution remplace les sorties des cas exécutés : il n'y a pas
une collection de conversions datées dispersées dans `dist/`.

## Deux cas de police, un seul original

Original commun : [fugaz-one.docx](original/abx2t/fugaz-one.docx).

| Cas | Préparation | Sortie | Résultat attendu |
|---|---|---|---|
| 1 — police absente | Fugaz One absente du système et de `custom-fonts/` | [01-missing-font.pdf](converted/fonts/01-missing-font.pdf) | Aucun plantage ; utilisation d'une police de substitution |
| 2 — police ajoutée | Copier le TTF dans `custom-fonts/` du même exécutable, sans effacer son cache | [02-manually-added-font.pdf](converted/fonts/02-manually-added-font.pdf) | Aucun plantage ; index actualisé automatiquement ; Fugaz One utilisée et embarquée dans le PDF |

La police est [Fugaz One](fonts/fugaz-one/FugazOne-Regular.ttf), Copyright (c) 2011
LatinoType Limitada, sous [SIL OFL 1.1](fonts/fugaz-one/OFL.txt). Elle est fournie
sans modification avec sa licence et ses noms réservés. Le DOCX ne l'embarque pas.
Le test ne l'installe pas dans le système et ne modifie pas l'algorithme existant.

Ajout manuel existant, depuis la racine du dépôt :

```sh
mkdir -p /dossier/de/Abx2t/custom-fonts
cp testdata/fonts/fugaz-one/FugazOne-Regular.ttf /dossier/de/Abx2t/custom-fonts/
/dossier/de/Abx2t/Abx2t testdata/original/abx2t/fugaz-one.docx exemple.pdf
```

Cette version n'expose pas d'option `--font` dans l'aide du wrapper. Le mécanisme
`custom-fonts/` est conservé. Le DOCX du test se régénère à l'identique avec
`python3 build/font_test.py --write-fixture`.

## Exécuter localement

Les scripts utilisent tous ce même dossier par défaut :

```sh
python3 build/corpus_test.py --exe chemin/vers/Abx2t --offline --allow-known-content-issues
python3 build/font_test.py --exe chemin/vers/Abx2t
python3 build/cli_test.py --exe chemin/vers/Abx2t --test-timeout
```

Le corpus produit 38 conversions des 18 fichiers téléchargés : PDF, TXT, ODT,
XLSX, ODS, CSV et ODP selon l'entrée. Les deux tests de police produisent deux
PDF supplémentaires. `--case word-shapes` sélectionne un document. Les originaux
committés sont vérifiés par SHA-256 ; aucun document n'est téléchargé par les tests.

Les tests CLI couvrent les options, erreurs, chemins avec espaces/accents, jokers,
batch séquentiel et parallèle, collisions, erreurs partielles et timeout réel
sur Unix. Les outils absents et les scénarios non couverts sont consignés dans
`results/cli.json`. Les partages UNC/SMB réels et le repli du répertoire
inscriptible sur tous les systèmes ne sont pas simulés.

Les contrôles techniques ne constituent pas un verdict de fidélité visuelle :
l'utilisateur ouvre l'original et la sortie pour les comparer. Deux alertes de
contenu restent suivies : [#16](https://github.com/abnd-corp/AbX2T/issues/16), texte
arabe extrait du PDF, et [#17](https://github.com/abnd-corp/AbX2T/issues/17), texte
des formes omis du TXT. Par défaut elles font échouer le corpus ;
`--allow-known-content-issues` admet uniquement leurs deux signatures exactes,
les conserve dans le rapport et bloque tout nouvel échec. Les tests de police et
CLI n'ont pas cette exception.

## Exemple fourni avec une release

Le packaging archive **ce dossier `testdata/` tel quel**, avec ses originaux,
ses sorties, les deux cas de police, les rapports et les attributions :

```sh
python3 build/package_test_renders.py --platform macos-arm64
```

Seuls le ZIP `Abx2t-testdata-v<core>-<plateforme>.zip` et son SHA-256 vont dans
`dist/`, à côté de l'archive de l'exécutable. Ce dossier n'accueille pas d'autres
copies décompressées des conversions. Le futur pipeline de release pourra joindre
cette archive à la version. Aucun push ni lancement GitHub n'est nécessaire pour
préparer et contrôler cet ensemble localement.

Les droits respectifs des documents et de la police sont détaillés dans
[ATTRIBUTIONS.md](ATTRIBUTIONS.md). La licence du wrapper ne les remplace pas.
