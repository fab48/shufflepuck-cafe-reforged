# Moteur de Shufflepuck Café — spécification extraite du binaire ST

Rétro-ingénierie du code 68000 d'origine (version Atari ST, Loriciel/Brøderbund 1989),
extrait de la RAM en cours d'exécution. Toute valeur ci-dessous est lue dans le code
ou vérifiée contre deux captures mémoire.

## Espace de coordonnées

Rectangle plat. La perspective est un effet d'affichage, pas de simulation.

```
X : -226 .. +226     murs latéraux (réflexion)
Y :  ~-20 .. ~1500   profondeur ; petit = côté joueur, grand = côté adverse
     Y = 295         ligne de service du joueur
     Y = 1205        ligne de service de l'adversaire
```

## État du palet

| Adresse | Rôle |
|---|---|
| `$1B58C` | X |
| `$1B58E` | Y |
| `$1B590` | vitesse X (dX) |
| `$1B592` | vitesse Y (dY) |

## Boucle physique (fonction `0x010466`)

```
dX = borner(dX, -150, +150)
dY = borner(dY, -300, +300)

X += dX
Y += dY

si X < -226 :  son_rebond() ; dX = -dX ; X = -452 - X
si X > +226 :  son_rebond() ; dX = -dX ; X =  452 - X      (réflexion miroir)
```

## Service / remise en jeu (fonction `0x00FEB0`)

```
X = 0
Y = 295 si le joueur sert, 1205 sinon
dX = 0 ; dY = 0
```

## Réponse à la collision (fonction `0x00FEEC`)

C'est **tout le ressenti du jeu**. Chaque raquette porte un bloc de paramètres ;
la collision applique quatre coefficients, exprimés en pourcentages (dénominateur
`$19CE8` = 100) :

```
dX' = ( dX × Cxx  +  raquette.vX × Cxp ) / 100
dY' = ( raquette.vY × Cyp  -  dY × Cyy ) / 100
```

- **Cxx / Cyy** : ce qui **reste** de la vitesse du palet. Le `-` devant `dY × Cyy`
  produit l'inversion : le palet repart dans l'autre sens.
- **Cxp / Cyp** : ce que la **vitesse de la raquette** transmet. C'est pourquoi il
  faut *accompagner* le geste : raquette immobile, renvoi mou.

Un second jeu de quatre coefficients existe (`+$12..+$18`), sélectionné par le
drapeau `+$1A`. ⚠️ Ce drapeau est un **état d'exécution** (0 au café, 1 dans les
captures en match) ; ce qui le positionne n'est pas encore identifié.

## Bloc de paramètres d'une raquette

| Offset | Champ |
|---|---|
| `+$00` | X |
| `+$02` | Y |
| `+$04` | vitesse X |
| `+$06` | vitesse Y |
| `+$08` | dénominateur (100) |
| `+$0A` `+$0C` | Cxx, Cyy |
| `+$0E` `+$10` | Cxp, Cyp |
| `+$12`…`+$18` | second jeu (Cxx2, Cyy2, Cxp2, Cyp2) |
| `+$1A` | drapeau de sélection |

Joueur : bloc fixe en `$19CF4`.
Adversaire courant : pointé par `$1B5A4`.

## Table des neuf adversaires

Base `$19D14`, pas de **86 octets**. L'ordre suit la numérotation du café.

| # | Nom | Cxx | Cyy | Cxp | Cyp | Jeu 2 (Cxp2/Cyp2) |
|---|---|---|---|---|---|---|
| 0 | **Skip** | 17 | 20 | 28 | 34 | 0 / 0 |
| 1 | **Visine** | 20 | 30 | 41 | 80 | 0 / 0 |
| 2 | **Vinnie** | 25 | 40 | 28 | 23 | 0 / 0 |
| 3 | **Lexan** | 30 | 50 | 72 | 101 | 0 / 0 |
| 4 | **Eneg** | **97** | **100** | 70 | 130 | 0 / 0 |
| 5 | **Nerual** | 15 | 30 | 100 | 100 | 0 / 0 |
| 6 | **Bejin** | 10 | 37 | 49 | 102 | 0 / 0 |
| 7 | **Biff** | 13 | 40 | 72 | **184** | 0 / 0 |
| 8 | **DC3** | 15 | 16 | 15 | 16 | 0 / 0 |
| — | *Joueur* | 50 | 50 | 70 | 130 | 70 / 140 |

### Lecture

**Deux stratégies de difficulté, pas une.**

- **Eneg** conserve 97 % et 100 % de la vitesse du palet : l'échange ne ralentit
  jamais, le palet revient aussi vite qu'il est parti.
- **Biff** transmet **184 %** de sa vitesse de raquette — le maximum du jeu. Il
  frappe à près du double de son propre mouvement.

Ce sont précisément les deux adversaires que l'utilisateur, joueur de longue date,
a désignés comme les plus durs — sans avoir vu le code.

**Skip** (17/20/28/34) amortit tout et ne transmet presque rien : le plus facile.
**DC3** est parfaitement symétrique (15/16/15/16), cohérent avec son rôle de
partenaire d'entraînement réglable.

Le second jeu de coefficients annule la transmission de la raquette pour **tous**
les adversaires (Cxp2 = Cyp2 = 0) alors que le joueur y conserve 70/140. Il
correspond vraisemblablement à un contact passif, sans geste.

## Vérification

Deux captures mémoire prises au moment d'un point perdu, aux coins opposés :

| | X | Y | dX | dY |
|---|---|---|---|---|
| impact **bas-gauche** | **−207** | **−18** | −18 | −208 |
| impact **haut-droite** | **+212** | **+1500** | +5 | +229 |

X à −207 puis +212 : les deux juste en deçà des murs à ±226, là où se produit un
impact de coin. Y à −18 (derrière la ligne du joueur) puis +1500 (derrière la ligne
adverse). Les quatre valeurs sont cohérentes avec la description faite par
l'utilisateur avant toute analyse.

## Outils

- `tools/sweep.py` — balayage 68000 résilient (capstone M68K, 96 % de couverture)
- `tools/disasm.py` — fonctions, plages, références croisées
- `work/dump/loaded.ram` — RAM à base connue, via point d'arrêt + `savebin`
