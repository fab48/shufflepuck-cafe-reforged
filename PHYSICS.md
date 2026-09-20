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

---

# Intelligence artificielle des adversaires

Trois routines, toutes lues dans le code — aucune supposition.

## 1. Patrouille (`0x010802`) — le comportement au repos

La raquette adverse se déplace à vitesse constante et **rebondit sur les bornes de
sa zone**, chaque borne imposant sa propre vitesse de repart :

```
suivantX = X + vX ;  suivantY = Y + vY

si suivantX dépasse  $20(a6) :  X = $20(a6) ;  vX = -$26(a6)
si suivantX descend sous $1E(a6) :  X = $1E(a6) ;  vX =  $28(a6)
si suivantY dépasse  (1500 - $22(a6)) :  Y = ... ;  vY = -$2C(a6)
si suivantY descend sous (1500 - $24(a6)) :  Y = ... ;  vY =  $2A(a6)
```

Le code teste aussi `$8(a6) / 2` contre les murs à ±250 : **`$8(a6)` est la largeur
de la raquette**, et la moitié en est le demi-débattement. Champ résolu.

## 2. Recentrage (`0x01096C`)

Calcule le centre de la zone de patrouille et oriente la vitesse vers lui, puis
exécute un pas de patrouille. C'est le retour à la position de repos.

## 3. Anticipation (`0x010A02`) — la vraie IA

```
si dY du palet <= 0            : ne rien faire   (il s'éloigne)
si Y du palet <= 1500 - $4E    : attendre        (seuil de réaction)
si état du jeu != 3            : ne rien faire

copier l'état du palet dans un objet de simulation :
    $1AFBC..$1AFC2  <-  X, Y, dX, dY

erreur = aléatoire dans [-$4A(a6), +$4A(a6)]
simulation.X += erreur

répéter jusqu'à $50(a6) fois :
    avancer la simulation d'un pas de physique
```

L'adversaire **rejoue la physique réelle en avance rapide** pour savoir où le palet
arrivera. Sa prédiction est donc exacte par construction — la difficulté ne vient
pas d'une meilleure prédiction, mais de **l'erreur de visée**, du **seuil de
réaction**, de la **profondeur d'anticipation** et de la **taille de sa zone**.

## Paramètres d'IA (noms vérifiés via le pointeur `+$54`)

| Nom | Erreur `$4A` | Pas `$50` | Réagit à Y > | Largeur `$08` |
|---|---|---|---|---|
| **Skip** | **±50** | 92 | 300 | 100 |
| Vinnie | ±5 | 88 | 300 | 100 |
| **Visine** | 0 | 92 | **1120** | 100 |
| Lexan | ±34 | 70 | 300 | 100 |
| Nerual | 0 | 78 | 300 | **60** |
| Eneg | ±5 | 80 | 300 | **80** |
| **Bejin** | 0 | 80 | 300 | **50** |
| **Biff** | 0 | 91 | 300 | 100 |
| Dc3 | 0 | 92 | 300 | 100 |

## Zones de patrouille et vitesses de rebond

| Nom | Xmin | Xmax | Ymin\* | Ymax\* | vDroite | vGauche | vLoin | vPrès |
|---|---|---|---|---|---|---|---|---|
| Skip | −87 | −11 | 84 | 163 | 10 | 10 | 33 | 34 |
| Vinnie | −168 | 189 | 0 | 171 | 2 | 2 | 5 | 5 |
| **Visine** | −136 | 144 | 40 | 251 | **122** | **116** | **141** | **149** |
| Lexan | −136 | 23 | 58 | 171 | 22 | 42 | 43 | 61 |
| **Nerual** | **−220** | **220** | **0** | **290** | 4 | 5 | 4 | 4 |
| Eneg | −164 | −64 | 89 | 171 | 3 | 3 | 3 | 2 |
| **Bejin** | **0** | **0** | **0** | **0** | 2 | 3 | 10 | 10 |
| Biff | −77 | 81 | 124 | 274 | 10 | 10 | 10 | 10 |
| Dc3 | −200 | 200 | 150 | 150 | 3 | 3 | 10 | 10 |

\* soustraits de 1500 par le code.

## Recoupements avec le jeu connu

Chacun de ces points est une **prédiction du code confirmée par la description du
jeu**, établie indépendamment :

- **Bejin** : zone de patrouille **entièrement nulle** — elle ne déplace pas sa
  raquette. Elle joue par télékinésie. Et elle a la **plus petite raquette** (50).
- **Visine** : seuil de réaction à Y > 1120 contre 300 pour tous les autres, donc
  elle attend le dernier moment — mais ses vitesses de rebond (122 à 149) sont dix à
  cinquante fois celles des autres. Elle est décrite comme « très rapide ».
- **Skip** : erreur de visée **±50**, la plus forte du jeu, et la zone de patrouille
  la plus étroite (76 de large). Le plus facile, doublement.
- **Nerual** : erreur nulle, **zone la plus large du jeu** (−220 à +220, toute la
  table), et il renvoie à 97/100 % de la vitesse reçue. Il « copie la puissance des
  tirs ».
- **Biff** : erreur nulle, anticipation profonde (91 pas), et 184 % de transmission.
- **Dc3** : `Ymin = Ymax = 150` — il ne bouge qu'en largeur, à profondeur fixe.
  Comportement de partenaire d'entraînement.

## Ce qui reste à établir

- `$2E`…`$34`, `$36`…`$48` : rôle non lu (fonctions `0x010AB6`, `0x015294` les lisent).
- `$4C` : non nul seulement pour Skip (10) et Lexan (5).
- Le drapeau `+$1A` : qui le positionne.
- La mécanique de fatigue.
- La projection en perspective.
- Les sons : points d'entrée `$11486` (rebond mur), `$11514`, `$114E4` identifiés
  avec leurs appelants ; correspondance événement→son à compléter.
