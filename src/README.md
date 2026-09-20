# Transcription en C

Transcription lisible du moteur, à partir de la rétro-ingénierie documentée dans
`../PHYSICS.md`. Chaque constante provient du binaire d'origine.

| Fichier | Contenu |
|---|---|
| `shufflepuck.h` | constantes du terrain, structures, prototypes |
| `shufflepuck.c` | physique, collision, raquette du joueur, projection, table des neuf adversaires |

## ⚠️ Non compilé

Aucun compilateur C n'est installé sur la machine de développement. **Ce code n'a
jamais été compilé ni exécuté.** Il est transcrit du désassemblage et relu, pas testé.

Pour le construire :

```
pacman -S mingw-w64-x86_64-gcc      # sous MSYS2
gcc -c -Wall -Wextra shufflepuck.c
```

## Vérifications déjà effectuées

La logique a été remontée en Python et confrontée aux valeurs publiées dans
`PHYSICS.md` :

- courbe d'accélération de la souris : 1, 6, 16, 48, 160 — **a corrigé une erreur de
  la documentation**, qui annonçait 5 au lieu de 6 pour un écart de 4
- projection : centre à 160 à toute profondeur, table de 199 px à 101 px

## Ce qui n'est pas encore transcrit

- l'IA (patrouille, recentrage, anticipation) et la machine à états
- le service et ses cas particuliers (Bejin, Biff)
- l'ivresse de Lexan
- la projection en ordonnée, dont la formule reste non validée

## Réserve sur l'arithmétique

L'original emploie `MULU` (multiplication non signée) sur un opérande pouvant être
négatif, suivi de `DIVS`. Le comportement aux valeurs extrêmes n'a pas été confronté au
matériel. Sur la plage de jeu normale, la transcription est fidèle.
