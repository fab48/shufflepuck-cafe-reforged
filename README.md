# Shufflepuck Café — rétro-ingénierie complète

Projet personnel de préservation, à partir d'un exemplaire d'origine possédé
(Atari STF, édition Loriciel/Brøderbund, 1989).

L'objectif est de **tout désassembler et tout réécrire**, pour pouvoir en
faire une version moderne sur les plateformes d'aujourd'hui — et non de
bricoler une émulation habillée.

## Règle du projet

**Aucune affirmation sans les octets qui la portent.** Chaque offset, chaque
format, chaque constante est accompagné de sa preuve. Les hypothèses sont
étiquetées comme telles. Les erreurs sont corrigées dans le texte, avec leur
cause — il y en a une quinzaine de documentées dans `FINDINGS.md`, et c'est
volontaire : savoir *comment* on s'est trompé vaut la correction elle-même.

## Où en est le travail

### Le moteur

Physique du palet, collision, IA des neuf adversaires, machine à états,
service, pilotage de la raquette à la souris, projection en perspective,
architecture audio, ivresse de Lexan — établis et transcrits en C lisible
(`src/`). La table des neuf adversaires n'est pas recopiée à la main : elle
est **générée** depuis la mémoire du jeu.

La nomenclature des champs vient des auteurs eux-mêmes : Loriciel a livré le
jeu avec son **éditeur de réglages** encore dedans, une table de widgets à
`0x01A118` où chaque paramètre porte son libellé français et ses bornes.

### Les assets

Les deux disquettes n'ont **aucun système de fichiers** : la FAT est
blanchie, le répertoire vide, et le jeu lit par secteur absolu. Chaque format
a donc été reconnu par sa signature, puis **vérifié** par une égalité de
taille exacte.

| Format | Ce que c'est | État |
|---|---|---|
| `.PC1` | Degas Elite compressé (PackBits) | 5 écrans extraits |
| `.CPL` | RLE à convention inversée | `barsprit` (57 sprites), `sprites` (28) |
| `.TC0` | codage par paires d'octets | **les 9 adversaires**, 136 sprites |
| `.ECH` | banque sonore | musique + bruitages, 33 sons |

Disquette 1 : **98 % expliqué** (dont 19 % de programme).
Disquette 2 : **96 % expliqué**.

Les `.TC0` portent chacun les images **et la voix** de leur personnage.

Le son numérisé sur un STF, qui n'a pas de DMA audio : chaque octet de
l'échantillon indexe un triplet de volumes des trois voies du YM2149 dans une
table de 256 entrées, et le Timer A en consomme un par tic. Le rebond du
palet n'est pas vingt-trois sons enregistrés mais **un seul**, transposé en
changeant le diviseur du timer.

### Le code

**76 % du code réellement chargé** est atteint par désassemblage récursif,
411 fonctions. Le gisement décisif : ce compilateur ouvre chaque fonction par
`link a5,#-N`, et un `4E 55` précédé d'un `rts` est une fonction, pas un
hasard.

### Le prototype

`web/` — un prototype jouable dans un navigateur, sur la physique
transcrite et les décors d'origine. Trois endroits y sont signalés comme
**reconstruction** et non transcription, parce qu'ils ne sont pas lus dans
l'original. Voir `web/README.md`.

## Organisation

```
PHYSICS.md    la spécification du moteur — le livrable principal
FINDINGS.md   le journal, avec les preuves et les erreurs
ASSETS.md     les formats de fichiers et ce qui en a été tiré
src/          le moteur en C lisible
web/          le prototype navigateur
tools/        les outils d'analyse et d'extraction
run/          la configuration Hatari, pour jouer à l'original
work/         les données dérivées du jeu (seul work/assets/ est versionné)
```

## Jouer

**En ligne** : <https://fab48.github.io/shufflepuck-cafe-reforged/> — publié
automatiquement depuis `web/` à chaque push (`.github/workflows/pages.yml`).

**En local** — il faut un serveur, les modules JavaScript ne se chargent pas
depuis un fichier ouvert directement :

```bash
python -m http.server 8731 --directory D:/projets/shufflepuck/web
```

ou double-cliquer sur `run/web.bat`.

## Ce qui est versionné

Les assets tirés des disquettes sont versionnés tels quels : `web/assets/`
(planches de sprites, décors, sons, manifeste) et `work/assets/` (le produit
brut de l'extraction). Le reste de `work/` — images de disquettes, dumps
mémoire, captures — reste en local : il se reconstitue depuis ses propres
disquettes.

Le code de rétro-ingénierie est à nous ; les images, les sons et les données
du jeu ne le sont pas. Le jeu reste la propriété de ses ayants droit (chaîne
Brøderbund → The Learning Company → Mattel → Gores → Ubisoft pour le
catalogue ludique, 2001 — jamais réédité depuis 1989). Les assets ont été
extraits d'un exemplaire d'origine possédé.
