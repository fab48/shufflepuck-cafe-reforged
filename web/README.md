# Le moteur en web

Un prototype jouable qui tourne sur les **assets d'origine** et la
**physique retro-ingénierée**. Ce n'est pas encore le jeu : c'est la boucle
centrale, vérifiable.

## Lancer

Depuis la racine du projet :

```bash
python -m http.server 8731 --directory web
```

puis <http://localhost:8731>. Cliquer sur l'écran capture la souris —
c'est le seul moyen d'avoir le déplacement relatif que le jeu attend.

## Ce qui est transcrit du 68000

`moteur.js` suit `src/shufflepuck.c` et `src/ia.c` ligne à ligne, avec
l'adresse d'origine en commentaire pour chaque routine :

| | |
|---|---|
| `$010466` | un pas de physique du palet, bornage **avant** l'intégration |
| `$00FEEC` | la collision : réflexion + accélération, en pourcentages |
| `$00FB7A` | la raquette du joueur, avec sa courbe d'accélération |
| `$010802` | la patrouille |
| `$01096C` | le recentrage |
| `$010A02` | l'anticipation — l'IA rejoue la vraie physique en avance rapide |
| `$010AB6` | la poursuite |
| `$010BCE` | la frappe |
| `$0110BA` | l'ivresse de Lexan |
| `$00DB9C` | la projection en abscisse |
| `$00DBC2` | la projection en ordonnée |
| `$011486` | la séquence de rebond selon la profondeur |

Un détail qui compte : le 68000 divise en **tronquant vers zéro** (`DIVS`).
`Math.floor` arrondit vers le bas, ce qui diffère pour les négatifs. Tout
passe par `div()`.

Les paramètres des neuf adversaires ne sont pas recopiés : ils sont lus
dans la table `$19D14` du dump mémoire par `tools/exporter_web.py` et
écrits dans `assets/manifeste.json`.

## Ce qui est une reconstruction, et non une transcription

Trois endroits sont signalés comme tels dans le code, parce qu'ils ne
sont **pas** lus dans l'original :

1. **Les transitions de la machine à états.** Le répartiteur `0x010EAA` et
   la liste des états sont établis, mais pas les conditions de passage
   entre anticipation, poursuite et recentrage.
2. **Le bornage de la cible de poursuite** dans la zone de l'adversaire.
3. **`contraindre()`**, qui ramène la raquette adverse dans sa zone après
   chaque mouvement. Sans lui, la frappe — qui vise une cible dispersée au
   hasard — emmène la raquette hors de la table. L'original contient
   forcément l'équivalent ; je ne l'ai pas encore trouvé.

Contrôle : sur 3 000 images et les neuf adversaires, **aucune sortie de
zone**, et les renvois vont de 0 (Eneg) à 142 sur 142 (Nerual, Bejin).

## Ce qui n'est pas encore là

- Les sprites des raquettes ne sont pas identifiés dans les banques : elles
  sont dessinées en ellipse de repère.
- Les palettes propres à chaque adversaire. Tout est rendu avec celle du
  terrain, ce qui fausse les couleurs des personnages.
- Le service de l'adversaire, l'indice sonore de Bejin, l'adaptation de
  Biff au score, la vitre qui se brise.
- L'identification des neuf `.TC0` aux neuf noms : ils sont numérotés par
  position sur la disquette, et la correspondance n'est **pas** établie.

## Les assets

`assets/` est produit par `tools/exporter_web.py` depuis `work/`. Rien n'y
est redessiné : les images sortent telles qu'elles sont sur les disquettes,
à la conversion de palette près (`$0RGB` 3 bits → RGB 8 bits). L'upscale et
le recolorage se feront sur ces fichiers-là.

Le rebond du palet est joué par transposition — un seul échantillon, dont
on change le `playbackRate`, exactement comme le ST changeait le diviseur
du Timer A.
