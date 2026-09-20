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

---

# Machine à états de l'adversaire

## Le répartiteur (`0x010EAA`)

```
a6 = [$1B5A4]                    bloc de l'adversaire courant
$1AFC8 = (a6)                    position X de sa raquette
$1AFCA = $2(a6)                  position Y
aiguiller sur $1B598             <- variable d'etat
```

Chaque branche appelle sa routine **et positionne le drapeau `+$1A`**, qui sélectionne
le jeu de coefficients utilisé lors d'une collision.

| État → routine | `+$1A` | Conséquence au contact |
|---|---|---|
| `0x10A02` anticipation | 1 | jeu 2 → **aucun transfert de puissance** |
| `0x10AB6` poursuite | 1 | jeu 2 |
| `0x1096C` recentrage | 1 | jeu 2 |
| `0x10D44` (à identifier) | 1 | jeu 2 |
| **`0x10BCE` frappe** | **0** | **jeu 1 → transfert complet** |
| **`0x10C7C` frappe** | **0** | **jeu 1 → transfert complet** |

**Mécanique centrale :** l'adversaire ne transmet sa vitesse de raquette au palet que
s'il est **en train de frapper**. Dans tous les autres états, le contact se contente
d'amortir. C'est la contrepartie exacte de ce que fait le joueur en accompagnant son
geste.

## Les deux états de frappe

Même structure dans les deux : approche de la cible mémorisée (`$1AFC4`/`$1AFC6`) par
pas bornés à **`±$36(a6)`** en X et **`±$38(a6)`** en Y — un bornage **symétrique**,
distinct de celui de la poursuite. Arrivé à destination, l'état passe à 6.

## Fonction utilitaire `0x00FDEC`

```
borner(min, valeur, max)   ->  min si valeur < min
                               max si valeur > max
                               valeur sinon
```
Lue dans le code, pas supposée. Utilisée par toutes les routines de déplacement.

## Vitesses de déplacement, par adversaire

| Nom | Poursuite X | Poursuite Y | **Frappe X** | **Frappe Y** |
|---|---|---|---|---|
| **Skip** | **8 / 8** | **6 / 9** | 13 | 14 |
| Vinnie | 26 / 29 | 32 / 26 | **3** | **5** |
| Visine | 74 / 77 | 37 / 48 | 139 | 145 |
| **Lexan** | **120 / 128** | **106 / 113** | 89 | 88 |
| **Nerual** | 58 / 53 | 61 / 82 | **161** | **238** |
| Eneg | 123 / 65 | 77 / 71 | 13 | 14 |
| Bejin | 69 / 72 | 83 / 83 | 13 | 14 |
| **Biff** | 66 / 64 | 64 / 63 | 13 | 14 |
| Dc3 | 17 / 17 | 17 / 17 | 14 | 14 |

- **`$2E` / `$30`** : pas max vers la gauche / la droite pendant la poursuite
- **`$34` / `$32`** : pas max vers l'avant / l'arrière pendant la poursuite
- **`$36` / `$38`** : pas max pendant la frappe (symétrique)

## Lecture

**Skip** est lent sur trois plans à la fois : poursuite à 8 (le minimum), erreur de
visée ±50 (le maximum), et la zone de patrouille la plus étroite du jeu.

**Lexan** a la poursuite la plus rapide (120/128) — cohérent avec un adversaire qui
perd ses réflexes en s'enivrant : il *part* très rapide.

**Nerual** frappe le plus vite du jeu (161/238), sans erreur de visée, depuis la zone
la plus large, et renvoie à 97/100 % de la vitesse reçue.

**Biff** est modeste partout — poursuite 66/64, frappe 13/14. Sa difficulté ne vient
**pas** de sa vitesse mais de ses **184 % de transfert de puissance**. Il ne court pas
après le palet : il cogne. Cohérent avec le personnage, un biker massif.

**Vinnie** a la frappe la plus lente du jeu (3/5) : il ne bouge presque plus au moment
de toucher.

**Dc3** est uniforme partout (17 en poursuite, 14 en frappe) — le partenaire
d'entraînement neutre.

---

# Service et cas particuliers (`0x010D44`)

Un compteur `$19D12` décompte à chaque appel ; à zéro il est rechargé à **30** et la
routine choisit une cible de service.

## Cas général — tous sauf Bejin et Biff

```
cible_X = aleatoire( $42(a6) , $44(a6) )
cible_Y = aleatoire( $46(a6) , $48(a6) )  +  1205
```

`$42`/`$44` et `$46`/`$48` sont les **bornes de la cible de service**.

## Bejin (`$1B5AC == 6`) — le service télékinésique

```
$1B5B2 = aleatoire & 1
$1B5B4 = aleatoire & 1          <- decide la direction
$1B598 = 6
jsr $115DE( $1B5B4 )            <- SON choisi par ce meme tirage
```

Deux bits tirés au hasard, et **le son joué dépend du bit qui décide de la
direction**. C'est l'indice sonore : écouter son service permet de l'anticiper.
La mécanique est confirmée dans le code d'origine.

## Biff (`$1B5AC == 7`) — adaptation au score

```
ecart = $1B58A - $1B588                    difference de score
pas   = borner(-10, ecart, +10) + 10       ->  0 a 20

cible_X = $44(a6) * pas / 20               signe aleatoire
cible_Y = $46(a6) + ($48 - $46) * pas / 20  + 1205
```

**Le service de Biff s'ajuste à l'écart de score.** C'est une adaptation au
déroulement du match, pas une dégradation dans le temps.

## Bornes de cible de service

| Nom | `$42` | `$44` | `$46` | `$48` |
|---|---|---|---|---|
| Skip | -18 | 15 | 88 | 120 |
| Vinnie | -50 | 11 | 84 | 127 |
| Visine | -230 | 1 | 26 | 59 |
| Lexan | -86 | -5 | 103 | 206 |
| Nerual | -11 | 13 | 22 | 55 |
| Eneg | -87 | 67 | 136 | 231 |
| Bejin | 0 | 0 | 49 | 49 |
| Biff | 0 | 104 | 84 | 300 |
| Dc3 | -86 | 72 | 109 | 218 |

---

# Résultat négatif vérifié : pas de fatigue par dégradation

Recherche exhaustive des écritures dans le bloc adverse (registre chargé depuis
`$1B5A4`) : **11 écritures au total**, portant uniquement sur

- `+$00` `+$02` position de la raquette
- `+$04` `+$06` sa vitesse
- `+$1A` le drapeau de sélection
- `+$1C` un indicateur

**Aucun code n'écrit dans `+$08` à `+$18`.** La largeur de raquette, les coefficients
de collision et les vitesses sont des **constantes en lecture seule** pendant toute la
partie.

Il n'existe donc **pas** de mécanique dégradant progressivement les capacités d'un
adversaire. L'« ivresse » de Lexan et « l'usure » de Biff, si elles se traduisent par
autre chose qu'une animation, passent par un autre chemin — pour Biff, c'est
l'adaptation au score ci-dessus.

Noté comme résultat négatif afin de ne pas implémenter dans le remake une mécanique
que l'original ne contient pas.

---

# Sons

## Architecture

Un **lecteur unique**, `$112C0`, appelé **44 fois** dans tout le code. Signature :

```
jouer( identifiant , drapeaux )       drapeaux = 0x80 le plus souvent
```

Toutes les routines sonores y aboutissent. Il n'y a pas d'autre chemin vers le son.

## Correspondances établies

| Identifiant | Événement | Preuve |
|---|---|---|
| `0x080` | **rebond sur un mur latéral** | joué par `$11486`, appelé depuis la routine de rebond du palet (`0x0104D0`, `0x0104F8`) |
| `0x11A` | **frappe de raquette** | joué par `$114E4`, appelé depuis le test de collision (`0x0102C2`) |
| `0x200` / `0x201` | **les deux services de Bejin** | `$115DE` choisit l'un ou l'autre selon le bit aléatoire de direction |

Les trois sont adossées à un contexte d'appel déjà identifié par ailleurs, pas à une
supposition.

## Familles d'identifiants

| Plage | Nature |
|---|---|
| `0x001` `0x002` `0x003` | interface / menu (appelés depuis `0x11378`–`0x11422`) |
| `0x080` | rebond mur |
| `0x100`–`0x103` | seconde série d'effets (`$1151C`, `$11586`) |
| `0x11A` | frappe |
| `0x200`–`0x207` | **réactions des adversaires** |

## La famille `0x2xx`

Une vingtaine de petites fonctions enveloppes, de `$1160A` à `$118E8`, jouent chacune
un ou plusieurs identifiants entre `0x200` et `0x207`. Leur régularité — deux à trois
sons par fonction, une vingtaine de fonctions pour neuf adversaires — correspond aux
**réactions par personnage** : victoire, défaite, raillerie.

⚠️ **La correspondance enveloppe → adversaire n'est pas encore établie.** Elle demande
de remonter aux appelants de chacune de ces fonctions. Non fait, donc non affirmé.

## Ce que ça donne pour le remake

Le son du rebond et celui de la frappe sont les deux effets du cœur de jeu, et ils
sont identifiés. Le tell sonore de Bejin l'est aussi, avec ses deux identifiants —
c'est la mécanique la plus fine du jeu et elle est reproductible telle quelle.
