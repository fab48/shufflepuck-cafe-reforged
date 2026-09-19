# Shufflepuck Café — jouer, puis remastériser

Projet personnel de préservation et de rétro-ingénierie, à partir d'un exemplaire
d'origine possédé (Atari STF, édition Loriciel/Brøderbund).

## Deux pistes distinctes

**1. Jouer** — la version Atari ST, en couleurs, celle des souvenirs.
Hatari lit le `.stx` tel quel, protection comprise. Voir `run/`.

**2. Remastériser** — sur la base de la **version Macintosh**, via la
recompilation statique de https://github.com/sp00nznet/shufflepuck-cafe
(le binaire 68k Mac relevé en C natif). Ce dépôt en est à la phase 5 :
ça compile, ça tourne, ça dessine, mais ce n'est pas encore jouable.

Ces deux pistes ne se rejoindront pas : voir la section « Pistes écartées »
de `FINDINGS.md` pour le raisonnement.

## Organisation

```
FINDINGS.md   journal de rétro-ingénierie — chaque fait avec ses octets
tools/        scripts d'analyse
work/         données dérivées du jeu (non versionné)
run/          configuration Hatari
docs/         notes au long cours
```

## Aucune donnée du jeu n'est versionnée

`work/` est exclu du dépôt. Le jeu reste la propriété de ses ayants droit
(chaîne Brøderbund → The Learning Company → Mattel → Gores → Ubisoft pour le
catalogue ludique, 2001 — jamais réédité depuis 1989). Usage strictement privé,
sur la base d'un exemplaire d'origine possédé.
