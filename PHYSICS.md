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

Base `$19D14`, pas de **86 octets**.

### ⚠️ L'ordre des blocs n'est PAS celui du café

Correction d'une erreur : j'avais supposé que l'ordre des blocs suivait la
numérotation des zones cliquables du café. **C'est faux.** Chaque bloc contient en
`+$54` le mot bas d'un **pointeur vers son nom** (base `0x010000`), ce qui permet de
lire l'identité au lieu de la supposer.

| Bloc | Ce que j'avais supposé | Nom réellement pointé |
|---|---|---|
| 1 | ~~Visine~~ | **Vinnie** |
| 2 | ~~Vinnie~~ | **Visine** |
| 4 | ~~Eneg~~ | **Nerual** |
| 5 | ~~Nerual~~ | **Eneg** |

### Table vérifiée

| # | Nom | Adresse | Cxx | Cyy | Cxp | Cyp | `+$08` |
|---|---|---|---|---|---|---|---|
| 0 | **Skip** | `$19D14` | 17 | 20 | 28 | 34 | 100 |
| 1 | **Vinnie** | `$19D6A` | 20 | 30 | 41 | 80 | 100 |
| 2 | **Visine** | `$19DC0` | 25 | 40 | 28 | 23 | 100 |
| 3 | **Lexan** | `$19E16` | 30 | 50 | 72 | 101 | 100 |
| 4 | **Nerual** | `$19E6C` | **97** | **100** | 70 | 130 | 60 |
| 5 | **Eneg** | `$19EC2` | 15 | 30 | 100 | 100 | 80 |
| 6 | **Bejin** | `$19F18` | 10 | 37 | 49 | 102 | 50 |
| 7 | **Biff** | `$19F6E` | 13 | 40 | 72 | **184** | 100 |
| 8 | **Dc3** | `$19FC4` | 15 | 16 | 15 | 16 | 100 |
| — | *Joueur* | `$19CF4` | 50 | 50 | 70 | 130 | 100 |

### Lecture

**Nerual** conserve **97 % et 100 %** de la vitesse du palet : il le renvoie
pratiquement à la vitesse où il l'a reçu. C'est exactement la description qu'en donne
la documentation du jeu — *« capable de copier la puissance des tirs du joueur »*.
La correction de l'ordre des blocs fait coïncider les chiffres avec le personnage.

**Biff** transmet **184 %** de sa vitesse de raquette, le maximum du jeu.

**Eneg** amortit fortement l'entrant (15/30) mais transmet intégralement son geste
(100/100) : un profil de frappeur, pas de renvoyeur.

**Skip** amortit tout et ne transmet presque rien. **Dc3** est parfaitement symétrique
(15/16/15/16), cohérent avec son rôle de partenaire d'entraînement réglable.

## Autres champs du bloc (86 octets)

34 offsets varient d'un adversaire à l'autre. Identifiés avec certitude :

| Offset | Contenu |
|---|---|
| `+$0A` `+$0C` `+$0E` `+$10` | Cxx, Cyy, Cxp, Cyp |
| `+$12` `+$14` `+$16` `+$18` | second jeu de coefficients |
| `+$1A` | drapeau de sélection (état d'exécution) |
| `+$54` | pointeur vers le nom (mot bas, base `0x010000`) — **vérifié** |

Hypothèses à confirmer :

- **`+$08`** vaut 100 partout sauf Nerual (60), Eneg (80), Bejin (50). Ce n'est **pas**
  le dénominateur des pourcentages — celui-ci est le global `$19CE8`, lu dans le code.
  Rôle inconnu.
- **`+$1E`…`+$24`** : quatre valeurs par adversaire, nulles pour **Bejin**. Cohérent
  avec un personnage qui ne déplace pas sa raquette (télékinésie) — donc probablement
  des **bornes de déplacement**.
- **`+$26`…`+$34`** : **Visine** y porte les valeurs les plus élevées du jeu
  (122, 116, 141, 149). Sa description la dit « très rapide ». Probablement des
  **vitesses de déplacement**.
- **`+$4E`** vaut 1200 pour tous sauf **Visine** (380).

Ces trois dernières lignes sont des **corrélations**, pas des lectures de code. À
confirmer en désassemblant les routines qui lisent ces offsets.
