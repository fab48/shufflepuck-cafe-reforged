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

---

# Projection en perspective

Deux fonctions, appelées **par paires** depuis les mêmes endroits (`0xDC6E`/`0xDC7E`,
`0xDC94`/`0xDCA4`, `0xDEDC`/`0xDEBC`).

## Abscisse — `$DB9C(X, Y)` ✅ vérifiée

```
ecranX = X * 411 / (Y + 643) + 160
```

Division de perspective à un point de fuite. `160` est le centre d'un écran de 320.

### Vérification indépendante

La formule vient du code ; les bornes du terrain (`X = ±226`, `Y` de 295 à 1205)
viennent de la routine de physique, trouvée séparément. Les deux se recoupent :

| Profondeur | Mur gauche | Centre | Mur droit | Largeur |
|---|---|---|---|---|
| Y = 295 (ligne joueur) | 60 | **160** | 259 | 199 |
| Y = 600 | 85 | **160** | 234 | 149 |
| Y = 900 | 99 | **160** | 220 | 121 |
| Y = 1205 (ligne adverse) | 109 | **160** | 210 | 101 |
| Y = 1500 (fond) | 116 | **160** | 203 | 87 |

Le centre tombe exactement sur 160 à toute profondeur, la table rétrécit
régulièrement, et tout reste dans `[0, 320]`. Deux résultats obtenus séparément qui
s'accordent.

## Ordonnée — `$DBC2(X, Y)` ⚠️ extraite, non validée

```
t      = Y * 207 / (Y + 970)
ecranY = (193 - t)  -  X * (164 - t) / 512
```

**Tranché — c'était ma lecture des arguments qui était fausse.**

J'avais supposé que le premier argument de cette fonction était l'abscisse, ce qui
faisait dépendre l'ordonnée de l'abscisse et inclinait absurdement le bord de la
table. Le site d'appel `0x00DC58`, qui projette les quatre coins d'un rectangle,
le dément :

```
00dc60  move.w  $a(a5), -(a7)      ; profondeur
00dc64  move.w  $8(a5), d3
00dc68  sub.w   $c(a5), d3         ; x - demi-largeur
00dc6c  move.w  d3, -(a7)
00dc6e  jsr     $db9c              ; projeter_X(x - demi, profondeur)

00dc76  move.w  $a(a5), -(a7)      ; MEME profondeur
00dc7a  move.w  $10(a5), -(a7)     ; et non $8(a5) : ce n'est pas l'abscisse
00dc7e  jsr     $dbc2              ; projeter_Y(hauteur, profondeur)
```

Les deux projections reçoivent **la même profondeur** en second argument. Mais le
premier argument de `projeter_Y` n'est pas `$8(a5)` — l'abscisse du rectangle — c'est
`$10(a5)`, puis `$E(a5)` pour l'autre coin : **deux hauteurs différentes**.

Le premier argument est donc une **hauteur**, pas une abscisse. La formule se lit :

```
t       = profondeur * 207 / (profondeur + 970)
ligneSol = 193 - t                          /* l'ordonnée du sol à cette profondeur */
ecranY   = ligneSol - hauteur * (164 - t) / 512
```

C'est une projection 2,5D ordinaire : une ligne de sol qui remonte avec la
profondeur, et un objet soulevé au-dessus d'elle d'une hauteur dont l'échelle décroît
avec la distance. **Aucune inclinaison.**

### Ce que l'image du terrain confirme, et ce qu'elle ne confirme pas

Le fichier `jeu.PC1` extrait de la disquette permet de mesurer le décor. Sur les
lignes 62 à 118, les bords de la table donnent :

- un centre à **159,5 sur chaque ligne sans exception** — le point de fuite est
  exactement l'abscisse 160, ce qui **confirme `SP_ECRAN_CENTRE` sur l'image
  elle-même** ;
- une demi-largeur linéaire en ordonnée à **0,67 pixel près** en moyenne, s'annulant
  à l'ordonnée 21.

La linéarité, en revanche, ne démontre rien sur la paramétrisation en profondeur :
des bords **droits** donnent mécaniquement une demi-largeur linéaire, quelle que soit
la façon dont la profondeur est convertie en ordonnée. J'ai d'abord cru y voir une
réfutation de la formule ci-dessus ; c'était une erreur de raisonnement.

Reste un écart réel : la formule place l'horizon à `193 - 207 = -14`, le décor le
place à `+21`. Trente-cinq pixels. L'explication la plus simple est que **le décor est
peint à la main** et n'est pas produit par le moteur — auquel cas il n'a aucune raison
d'obéir à ses constantes. Je ne sais pas trancher entre les deux et je ne l'invente
pas.

La formule de l'abscisse, elle, ne souffre aucun doute.

---

# Animation de la vitre brisée

`0x00F23A` initialise, `0x00F28C` anime : **13 éclats**, enregistrements de 14 octets
à partir de `$19B12`.

```
energie = (150 - dY_palet) / 4          <- vient de la vitesse a l'impact

pour chacun des 13 eclats, a chaque image :
    position_X += vitesse_X / 8
    position_Y += vitesse_Y / 8
    vitesse_Y  += 12                     <- gravite
tant qu'un eclat a une ordonnee < 150, l'animation continue
```

Le point d'origine des éclats vient de la projection du palet (`$DB9C`). L'énergie est
proportionnelle à la vitesse d'arrivée : plus le tir est violent, plus la vitre explose
loin.

---

# L'ivresse de Lexan

## Correction d'un résultat négatif antérieur

J'avais conclu qu'aucune mécanique ne dégradait progressivement un adversaire, en me
fondant sur l'absence d'écriture dans le bloc adverse (`+$08` à `+$18`). **La portée de
cette recherche était trop étroite** : la dégradation existe, elle passe par un jeu de
variables séparé.

## Le mécanisme (`0x0110BA`)

```
si $1B5AC != 3 (Lexan) : sortir

pour chacune des dix variables $1B5DC .. $1B5EE :
    v = v * 82 / 100
```

Dix variables réduites de **18 %**, et la réduction **se cumule** d'un appel au suivant.
Le code est gardé par un test explicite sur l'index de l'adversaire : **Lexan
uniquement**.

## Ce que sont ces dix variables ✅ vérifié

Relevées en cours de match, elles valent `22, 42, 43, 61, 120, 128, 113, 106, 89, 88`.
Ce sont **exactement les dix paramètres de vitesse de Lexan**, dans l'ordre :

| Adresse | Correspond à | Valeur | Rôle |
|---|---|---|---|
| `$1B5DC`…`$1B5E2` | `+$26`…`+$2C` | 22, 42, 43, 61 | vitesses de rebond (patrouille) |
| `$1B5E4`…`$1B5EA` | `+$2E`…`+$34` | 120, 128, 113, 106 | vitesses de poursuite |
| `$1B5EC`…`$1B5EE` | `+$36`, `+$38` | 89, 88 | vitesses de frappe |

Dix valeurs concordant dans l'ordre : la correspondance n'est pas fortuite.

**Lexan ralentit donc dans tous ses modes de déplacement simultanément** — patrouille,
poursuite et frappe. Il démarre avec la poursuite la plus rapide du jeu (120/128) et
se dégrade au fil du match.

## Déclenchement

Appelée depuis `0x00D440`, après un point marqué :

```
si $1B588 == 1  ->  boire
sinon, tirage a pile ou face  ->  boire une fois sur deux
```

Il ne boit donc pas systématiquement : la dégradation est probabiliste.

## ⚠️ Ce qui reste à tracer

Le chemin par lequel ces valeurs dégradées reviennent dans le bloc que lit l'IA n'est
pas encore identifié — celle-ci accède au bloc par le pointeur `$1B5A4`, pas à ces
adresses absolues. Le mécanisme et les valeurs sont certains ; la réinjection ne l'est
pas.

---

# Pilotage de la raquette du joueur (`0x00FB7A`)

La pièce maîtresse du ressenti côté joueur, et la dernière à avoir été trouvée.

## La routine

```
dx = $1A7B2 - 160            ecart de la souris au centre de l'ecran
dy = $1A7B4 - 100

dx = borner(dx, -32, +32)    ecart maximal par image
dy = borner(dy, -32, +32)

dx = dx + dx * |dx| / 8      <- courbe d'acceleration
dy = dy + dy * |dy| / 8
dx = borner(dx, -200, +200)
dy = borner(dy, -200, +200)

demi = $19CFC / 2                        demi-largeur de la raquette
X_nouveau = borner(X + dx, demi-250, 250-demi)
Y_nouveau = borner(Y - dy, 0, 300)       Y inverse

$19CF8 = X_nouveau - X                   la VITESSE est le deplacement reel
$19CFA = Y_nouveau - Y
$19CF4 = X_nouveau
$19CF6 = Y_nouveau
```

## La courbe d'accélération

`d' = d + d × |d| / 8`

| Écart souris | Déplacement raquette | Rapport |
|---|---|---|
| 1 | 1 | ×1,0 |
| 4 | 6 | ×1,5 |
| 8 | 16 | ×2,0 |
| 16 | 48 | ×3,0 |
| 32 | 160 | ×5,0 |

**Attention à l'ordre des opérations.** L'original calcule `|d| / 2` d'abord (décalage
arithmétique), puis multiplie, puis divise par 4. Regrouper en `d × |d| / 8` donne un
résultat différent en arithmétique entière — pour `d = 5`, 7 et non 8. La transcription
en C respecte l'ordre d'origine.

Les petits gestes sont au 1:1 — précision au ralenti. Les grands gestes sont amplifiés
cinq fois — explosivité. C'est le cœur du toucher du jeu.

## Deux conséquences à ne pas manquer

**La vitesse est le déplacement effectif, calculé après bornage.** Raquette plaquée
contre un mur, le déplacement est nul, donc la vitesse est nulle — et la formule de
collision ne transmet alors aucune puissance. Le jeu punit la frappe coincée **sans
qu'aucune ligne ne le prévoie** : c'est émergent.

**L'axe Y est inversé** : `Y - dy`. Souris vers le bas, raquette vers le joueur.

## Bornes

| | Min | Max |
|---|---|---|
| Écart souris par image | −32 | +32 |
| Déplacement après courbe | −200 | +200 |
| Position X | demi-largeur − 250 | 250 − demi-largeur |
| Position Y | 0 | 300 |

La demi-largeur vient de `$19CFC`, l'équivalent pour le joueur du champ `+$08` des
adversaires. Les murs à ±250 sont les mêmes que pour la patrouille adverse.

## Entrée souris

Position absolue lue en `$1A7B2` (X) et `$1A7B4` (Y), puis ramenée à un écart par
rapport au centre de l'écran (160, 100) — le jeu recentre la souris à chaque image.
Le matériel est servi par l'IKBD en `$FFFC00`/`$FFFC02` (fonction `0x0157E6`).

---

# Audio — architecture complète

## Le lecteur central (`$112C0`)

```
jouer( identifiant , parametre )

numero_echantillon = identifiant & 0x00FF
banque             = identifiant & 0x0300

si banque != banque_courante ($1A03E) :
    arreter, puis charger la banque via $14EDA
jouer_echantillon( numero, parametre )    via $14EEC
```

**Trois banques**, pointées par :

| Bits 8-9 | Pointeur | Contenu |
|---|---|---|
| `0x000` | `$1AFD0` | banque 0 — interface |
| `0x100` | `$1AFD4` | banque 1 — effets de jeu |
| `0x200` | **`$1B59C`** | banque 2 — **sons de l'adversaire courant** |

## Pourquoi il n'y a pas de correspondance enveloppe → personnage

Le pointeur de la banque 2 (`$1B59C`) est voisin de celui de l'adversaire courant
(`$1B5A4`) et **change avec lui**. Les vingt petites fonctions qui jouent `0x200` à
`0x207` sont donc **génériques** : « joue le son n° 0 à 7 de l'adversaire en cours ».

La correspondance que je cherchais **n'existe pas** — c'est la banque qui bascule.
Chaque adversaire dispose de **8 emplacements** pour ses réactions.

## La hauteur variable selon la distance ✅

Le ST ne sait pas transposer un son à la volée. La solution retenue est matérielle :
**22 échantillons distincts du même impact**, un par tranche de profondeur.

```
$11486 (rebond sur un mur lateral) :

    echantillon = borner( Y_palet / 68 + 4 , 4 , 25 )
    jouer( 0x100 | echantillon , 0x80 )
```

`Y` va de 0 à 1500, donc `Y / 68` découpe le terrain en 22 bandes. Plus le palet est
loin, plus le numéro d'échantillon est élevé.

Les deux branches selon le signe de `X_palet` jouent **exactement la même chose** —
vestige d'une spatialisation gauche/droite jamais terminée.

## Organisation de la banque 1

| Échantillon | Rôle |
|---|---|
| 0 – 3 | effets divers (`$1151C`, `$11586`) |
| **4 – 25** | **rebond sur mur, 22 profondeurs** |
| **26** (`0x11A`) | **frappe de raquette** — hauteur fixe |

La frappe ne varie pas avec la distance : `$114E4` joue toujours `0x11A`, et ses deux
branches sont également identiques.

## Correspondances établies

| Identifiant | Banque | Événement |
|---|---|---|
| `0x104` – `0x119` | 1 | rebond mur, selon la profondeur |
| `0x11A` | 1 | frappe de raquette |
| `0x200` – `0x207` | 2 | réactions de l'adversaire courant |
| `0x001` – `0x003` | 0 | interface / menu |
| `0x100` – `0x103` | 1 | effets divers, dont probablement la vitre |

## Reste à établir

- Lequel des `0x100`–`0x103` est le bris de vitre (`$11586` en joue deux, et il est
  appelé depuis `0x00F252`, dans la routine qui initialise les 13 éclats — piste forte).
- Le rôle du second paramètre (`0x80` partout, `0xA0` une fois, `0x4080` une fois).
- Les données d'échantillons elles-mêmes, non localisées.

## Format des banques — partiellement résolu

En-tête commun aux trois banques :

```
mot 0 : type (5, 5, 3)
mot 1 : NOMBRE d'echantillons  (banque 1 : 0x1C = 28)
puis une table d'offsets 32 bits, relatifs au debut de la banque
```

Les 28 annoncés par la banque 1 concordent avec les 27 identifiés dans le code
(0-3 divers, 4-25 rebonds, 26 frappe).

Routine de lecture `$14EEC` :

```
si numero >= $1AFEA : abandonner       nombre d'echantillons charges
pointeur = [ $1AFEE + numero*4 ]       table de pointeurs resolus
jouer(pointeur, parametre)             via $14DD0
```

### ⚠️ Extraction des échantillons : échec

Les valeurs de `$1AFEE` sortent espacées de **4 octets** (`0x0462AE`, `0x0462B2`,
`0x0462B6`…). Ce ne sont donc pas des adresses de données audio mais des entrées d'une
**seconde table de descripteurs**, de 4 à 6 octets chacun. Le format comporte un niveau
d'indirection de plus que supposé, et ma tentative d'extraction directe échoue sur les
28 échantillons.

`tools/extraire_sons.py` est conservé — sa logique de validation est bonne, seule
l'interprétation du descripteur est fausse. À reprendre après lecture de `$14DD0`.

## Voie praticable : capturer la sortie

Même conclusion que pour les graphismes. Les données sont empaquetées dans les deux
cas, et le format de stockage résiste ; en revanche **la sortie est toujours en clair** :

| | Stockage | Voie d'extraction |
|---|---|---|
| Graphismes | compressés | tampon d'affichage `$1B700`, ou `Alt+G` |
| Audio | empaqueté, indirection non résolue | **enregistrement de Hatari** |

Hatari sait enregistrer le son en WAV : raccourci `Alt+Y` (`keyRecSound = 121`), ou
`--sound-rec <fichier>`. Une partie jouée en enregistrant donne tous les sons réels,
sans décoder quoi que ce soit.

C'est moins élégant que de lire le format, mais c'est **fiable et vérifiable**, là où
une extraction fondée sur un format à moitié compris produirait des fichiers faux sans
qu'on s'en aperçoive.


## Correction et extension : la dégradation touche aussi la puissance

Recherche exhaustive du produit en croix `$FE9E` sur les 16 984 instructions :
**seules deux fonctions l'emploient**, la réponse à la collision (coefficients
variables) et `0x0110BA`. Il n'existe donc **aucune mécanique de fatigue générale**
dans le jeu — la dégradation progressive est propre à Lexan, et c'est prouvé par
l'absence de la primitive ailleurs.

Mais `0x0110BA` fait **17 appels**, pas 10 comme annoncé précédemment. Les sept
variables manquantes changent la portée de la mécanique :

| Adresses | Valeurs en match | Champs de Lexan |
|---|---|---|
| `$1B5C0`–`$1B5C6` | 30, 50, 72, 101 | **Cxx, Cyy, Cxp, Cyp** — ses coefficients de collision |
| `$1B5D4`, `$1B5D6` | −136, 23 | `+$1E`, `+$20` — ses **bornes de patrouille** |
| `$1B5DC`–`$1B5E2` | 22, 42, 43, 61 | `+$26`–`+$2C` — vitesses de rebond |
| `$1B5E4`–`$1B5EA` | 120, 128, 113, 106 | `+$2E`–`+$34` — vitesses de poursuite |
| `$1B5EC`, `$1B5EE` | 89, 88 | `+$36`, `+$38` — vitesses de frappe |
| `$1B600` | 34 | `+$4A` — erreur de visée (correspondance à confirmer) |

**Lexan se dégrade sur tous les axes à la fois** : il frappe moins fort, se déplace
moins vite, et sa zone de patrouille rétrécit. Chaque verre retire 18 % de tout.

### Ce qui est prouvé, ce qui ne l'est pas

**Prouvé :** 17 variables multipliées par 82/100, sous garde `$1B5AC == 3`.

**Fortement étayé :** quatre valeurs consécutives correspondant dans l'ordre aux quatre
coefficients de Lexan — une coïncidence de cet ordre est improbable.

**Non prouvé :** la correspondance de `$1B600`, établie par égalité de valeur seule.
Et toujours pas de chemin de réinjection identifié vers le bloc que lit l'IA.

### Correction d'une affirmation antérieure

Le passage plus haut disant que les coefficients sont « des constantes en lecture seule
pendant toute la partie » est **vrai pour la table `$19D14`** mais **faux en portée** :
une copie de travail existe et elle est dégradée.


---

# L'ivresse de Lexan — résolu par l'expérience

## Correction : ma question était mal posée

Je cherchais comment les valeurs dégradées étaient « réinjectées » dans le bloc lu par
l'IA. **Il n'y a pas de réinjection** : les deux structures n'en font qu'une.

Mesuré sur deux instantanés d'un même match contre Lexan (score final 11-10) :

```
$1B5A4  ->  0x1B5B6      et NON 0x19E16
```

Le pointeur d'adversaire désigne une **copie de travail** recopiée au début du match.
La table `$19D14` est un **modèle immuable** — c'est pourquoi elle reste intacte. Les
17 adresses dégradées tombent toutes exactement sur des champs de cette copie :

```
0x1B5C0 = +$0A Cxx      0x1B5DC..0x1B5EE = +$26..+$38 toutes les vitesses
0x1B5C2 = +$0C Cyy      0x1B5D4 = +$1E zone X min
0x1B5C4 = +$0E Cxp      0x1B5D6 = +$20 zone X max
0x1B5C6 = +$10 Cyp      0x1B600 = +$4A erreur de visee
```

## Mesure sur 21 points

| Champ | Début | Fin | Reste |
|---|---|---|---|
| `+$0A` Cxx amorti X | 30 | 7 | 23 % |
| `+$0C` Cyy amorti Y | 50 | 14 | 28 % |
| `+$0E` Cxp transfert X | 72 | 20 | 27 % |
| `+$10` Cyp transfert Y | 101 | 29 | 28 % |
| `+$26`–`+$2C` rebonds | 22, 42, 43, 61 | 5, 11, 11, 18 | 22–29 % |
| `+$2E`–`+$34` poursuite | 120, 128, 113, 106 | 35, 36, 33, 30 | 28–29 % |
| `+$36` `+$38` frappe | 89, 88 | 25, 25 | 28 % |

**Quinze champs réduits à 31 % en moyenne.** `0,82 ^ n = 0,31` donne **n ≈ 5,9** :
six verres bus sur 21 points, cohérent avec un tirage à pile ou face par point.

## Les trois champs qui augmentent

| Champ | Début | Fin |
|---|---|---|
| `+$1E` zone X min | −136 | **−201** |
| `+$20` zone X max | 23 | **29** |
| `+$4A` erreur de visée | 34 | **40** |

Sa **zone de patrouille s'élargit** et sa **visée se dégrade**. Il ne ralentit pas
seulement : il titube et il rate.

⚠️ Ces trois-là **ne suivent pas** le facteur 0,82 (−136 × 0,82 donnerait −111, pas
−201). Le mécanisme qui les modifie n'est pas identifié. Noté, pas inventé.

## Champs épargnés

`+$08` largeur de raquette, `+$22` `+$24` bornes en profondeur, `+$4E` seuil de
réaction, `+$50` profondeur d'anticipation : **inchangés**. Il garde sa taille, sa
portée et son intelligence — il perd ses moyens physiques.

## Courbe

| Verres | Capacités restantes |
|---|---|
| 1 | 82 % |
| 2 | 67 % |
| 3 | 55 % |
| 4 | 45 % |
| 6 | 30 % |
| 10 | 14 % |

Comme la vitesse du palet, elle, ne baisse pas, il cesse d'arriver à temps bien avant
d'atteindre le bas de la courbe.


## Modèle complet et vérifié

Les 17 appels n'utilisent **pas le même coefficient**. Je l'avais supposé d'après les
quatre premiers ; c'était faux.

| Champs | Coefficient | Effet |
|---|---|---|
| `+$0A` `+$0C` `+$0E` `+$10` (jeu 1) | **82/100** | puissance de frappe |
| `+$12` `+$14` (jeu 2) | **82/100** | idem, second jeu |
| `+$26`–`+$2C` rebonds | **82/100** | vitesses de patrouille |
| `+$2E`–`+$34` poursuite | **82/100** | vitesses de poursuite |
| `+$36` `+$38` frappe | **82/100** | vitesses de frappe |
| `+$1E` `+$20` zone X | **107/100** | sa zone **s'élargit** |
| `+$4A` erreur de visée | **105/100** | il vise **moins bien** |

Chaque verre le rend donc **18 % plus faible, 7 % plus dispersé, 5 % moins précis**.
Trois coefficients choisis séparément : c'est un réglage délibéré, pas un effet de bord.

### Vérification exacte

Modèle rejoué sur les valeurs de début, avec la troncature vers zéro de `DIVS` :

```
N = 5 verres  ->   0/19 champs reproduits
N = 6 verres  ->  19/19 champs reproduits EXACTEMENT
N = 7 verres  ->   0/19 champs reproduits
```

Dix-neuf champs indépendants prédits à l'entier près, et le modèle s'effondre
totalement d'un cran de part et d'autre. Exemple sur la zone de patrouille :

```
-136 -> -145 -> -155 -> -165 -> -176 -> -188 -> -201
```

Le match ayant fini 11-10, Lexan a bu **six fois en 21 points**.

### Implémentation

```c
/* Appelee apres un point, si $1B588 == 1 ou sur tirage a pile ou face.
 * Uniquement si l'adversaire courant est Lexan ($1B5AC == 3).
 */
static int degrader(int v, int num) {
    long r = (long)v * num;
    return (int)(r >= 0 ? r / 100 : -((-r) / 100));   /* DIVS tronque vers zero */
}

void lexan_boit(SpRaquette *r) {
    r->cxx  = degrader(r->cxx,  82);   r->cyy  = degrader(r->cyy,  82);
    r->cxp  = degrader(r->cxp,  82);   r->cyp  = degrader(r->cyp,  82);
    r->cxx2 = degrader(r->cxx2, 82);   r->cyy2 = degrader(r->cyy2, 82);
    r->vr_droite = degrader(r->vr_droite, 82);
    r->vr_gauche = degrader(r->vr_gauche, 82);
    r->vr_loin   = degrader(r->vr_loin,   82);
    r->vr_pres   = degrader(r->vr_pres,   82);
    r->pas_gauche  = degrader(r->pas_gauche,  82);
    r->pas_droite  = degrader(r->pas_droite,  82);
    r->pas_arriere = degrader(r->pas_arriere, 82);
    r->pas_avant   = degrader(r->pas_avant,   82);
    r->pas_frappe_x = degrader(r->pas_frappe_x, 82);
    r->pas_frappe_y = degrader(r->pas_frappe_y, 82);

    r->x_min = degrader(r->x_min, 107);   /* la zone s'elargit */
    r->x_max = degrader(r->x_max, 107);
    r->erreur_visee = degrader(r->erreur_visee, 105);  /* la visee se degrade */
}
```

Épargnés : largeur de raquette, bornes en profondeur, seuil de réaction, profondeur
d'anticipation. Il perd ses moyens physiques, pas sa lucidité.


---

# Dispersion du point de frappe (`+$3A`–`+$40`) — derniers champs résolus

`$FDCE(min, max)` est un tirage uniforme dans un intervalle :

```
d3 = max - min + 1
resultat = (aleatoire mod d3) + min
```

Dans la routine de poursuite, **dès que l'adversaire atteint la cible prédite** :

```
$1B598 = 2                              etat "arrive"
$1AFC4 = $1AFBC                         memoriser le point d'interception
$1AFC6 = $1AFBE

$1AFBC += alea( $3A(a6), $3C(a6) )      dispersion laterale
$1AFBE += alea( $3E(a6), $40(a6) )      dispersion en profondeur
```

Ce ne sont donc **pas** des bornes de zone mais la **dispersion du point de frappe** :
après avoir intercepté, l'adversaire se décale d'une quantité tirée au sort. C'est le
mécanisme qui fait varier ses angles de renvoi.

| Nom | Latéral min | Latéral max | Étendue | Profondeur min | max | Étendue |
|---|---|---|---|---|---|---|
| Skip | -60 | 66 | 126 | 34 | 30 | -4 |
| Vinnie | -151 | 158 | 309 | 193 | 293 | 100 |
| Visine | -55 | 58 | 113 | 45 | 93 | 48 |
| Lexan | -149 | 155 | 304 | 189 | 288 | 99 |
| Nerual | 0 | 0 | 0 | 0 | 0 | 0 |
| Eneg | -151 | 158 | 309 | 193 | 293 | 100 |
| Bejin | -156 | 165 | 321 | 202 | 306 | 104 |
| Biff | -152 | 159 | 311 | 194 | 294 | 100 |
| Dc3 | -156 | 165 | 321 | 202 | 300 | 98 |

## Lecture

**Nerual : 0, 0, 0, 0.** Aucune dispersion — il frappe exactement au point
d'interception qu'il a calculé. Avec son erreur de visée nulle, la zone de patrouille
la plus large du jeu et 97/100 % de restitution de vitesse, il est **mathématiquement
parfait**.

**Visine (113) et Skip (126)** ont les dispersions les plus faibles : leurs renvois
sont réguliers. Chez Visine cela compense sa réaction très tardive ; chez Skip cela ne
suffit pas face à son erreur de visée de ±50 et à ses vitesses minimales.

**Les six autres** se situent entre 304 et 321 : renvois très imprévisibles.

## ⚠️ Anomalie chez Skip

Sa dispersion en profondeur est `alea(34, 30)` — **borne haute inférieure à la borne
basse**. Le calcul `max - min + 1` donne −3, soit une division par un nombre négatif
dans `$FDCE`. Le résultat est imprévisible et n'était certainement pas voulu.

**Probable bogue de l'original.** Un portage fidèle doit décider s'il le reproduit ou
le corrige — le signaler plutôt que le gommer silencieusement.


---

# Audio — correction majeure : ce ne sont pas des échantillons

## Ce que j'avais écrit, et qui est faux

> « Le ST ne sait pas transposer un son à la volée. La solution retenue est
> matérielle : 22 échantillons distincts du même impact. »

**Les deux affirmations sont fausses.** J'avais déduit le format sans jamais regarder
les octets.

## Le format réel

La banque 1 entière fait **112 octets pour 28 sons** — impossible pour du PCM. Chaque
descripteur est une courte **séquence de paires `(commande, valeur)` terminée par
`$FF`** :

```
#0  01 54 ff        une paire
#2  00 45 03 45 ff  deux paires
#4  02 2c ff
```

Ce sont des **paramètres pour le YM2149**, le générateur de sons de l'Atari ST. Le
moteur audio est un petit interpréteur de séquences, pas un lecteur d'échantillons.

## Les 22 rebonds sont un seul son transposé

| Échantillon | Profondeur | Descripteur | Valeur |
|---|---|---|---|
| 4 | 0 | `02 2c` | 44 |
| 5 | 1 | `02 2e` | 46 |
| … | … | … | … |
| 25 | 21 | `02 82` | 130 |

Premier octet identique sur les 22, second strictement croissant de 44 à 130. C'est
**une seule sonorité jouée à 22 hauteurs différentes**.

Sur le YM2149 le registre de ton est une **période**, donc une valeur plus grande
produit un son **plus grave**. Plus le palet est loin, plus l'impact est sourd —
exactement l'effet décrit par le joueur.

*(Le rôle précis du premier octet — registre, forme d'onde ou instrument — reste une
interprétation, non une lecture du code du moteur audio.)*

## La frappe de raquette

Échantillon 26 : `02 a4`, soit une valeur de 164 — plus grave que n'importe quel
rebond. Même sonorité de base, hauteur fixe.

## Conséquence pour le remake

Il n'y a **aucun échantillon à extraire** pour les effets de jeu. Il faut reproduire
une sonorité YM2149 et la jouer aux 22 hauteurs tabulées ci-dessus — ou synthétiser
l'équivalent.

La musique de titre numérisée, elle, relève d'un autre mécanisme, non étudié.

---

# La boucle de jeu complète — corrections du 21 septembre 2026

Jusqu'ici les routines étaient transcrites **isolément**. Tout ce qui les
reliait avait été reconstruit à l'intuition dans le prototype web, et c'est
précisément ce qui ne se jouait pas comme l'original. Tout ce qui suit a été
lu dans le code.

## L'ordre d'une image (`0x00DAA4`)

```
raquette du joueur   $FD38 -> $FB7A
IA                   $10EAA
palet                $1034C   repartiteur sur l'etat du jeu $1B594
score / vitre        $D4D4
```

## La détection de collision — elle était inventée

**Raquette du joueur (`0x010096`).** On compare les positions de l'image
*précédente* (position − vitesse) pour savoir de quel côté du palet se trouvait
la raquette, puis on teste le franchissement **avec une marge de 24** :

```
cote   = (palet.y - palet.dy) > (joueur.y - joueur.vy)
touche = cote ? palet.y - 24 < joueur.y  :  palet.y + 24 > joueur.y
si touche et COLLISION(joueur) :
    palet.y = joueur.y +/- 24        ; le palet est repose contre la raquette
    si palet.y > 300 et palet.dy < 5 : palet.dy = 5
```

**Raquette adverse (`0x0101D0`)** — asymétrique, sans marge :

```
si (adv.y - adv.vy) > (palet.y - palet.dy) et adv.y <= palet.y et COLLISION(adv) :
    palet.y = adv.y - 3 ;  palet.dy = min(palet.dy, -5)
```

**`COLLISION` (`0x00FEEC`) renvoie un booléen**, et son test en X est
**balayé** : l'intervalle parcouru par le palet pendant l'image, en vitesse
relative à la raquette, élargi de 24 (le rayon du palet), doit chevaucher la
raquette. Ma version précédente testait un point fixe sans rayon — d'où les
palets qui traversaient la raquette du joueur.

## La réponse à la collision — une erreur d'arrondi

Chaque terme passe **séparément** par `0x00FE9E` (`a·b/c` en 16 bits) :

```
dx = dx*reflex_x/D  +  vx*accel_x/D
dy = vy*accel_y/D   -  dy*reflex_y/D
```

et non `(dx*reflex_x + vx*accel_x)/D`. En entiers, ce n'est pas la même chose.
`D` n'est pas une constante : c'est la variable `$19CE8`, qui vaut 100.

## Le palet ne sort jamais

À la fin de chaque image, `palet.y` est borné à `[-18, 1500]`. C'est `$D4D4`
qui constate qu'il est à un fond (`y <= 0` : point de l'adversaire,
`y >= 1500` : point du joueur), passe le jeu à l'état 5 et fait **alterner**
le service, quel que soit le marqueur.

## Le service — pas de clic

Les états 1 et 2 ramènent le palet au point de service (295 ou 1205) à
±15 en X et ±60 en Y par image, puis le posent immobile. **On sert en frappant
le palet.** Le bouton de la souris ne sert pas à servir : maintenu, il fait
passer la raquette du joueur au second jeu de coefficients (`$19D0E`, posé
dans `$FB7A`).

## La raquette du joueur

`Y` est borné à **`[0, 300]`**, pas autour de la ligne de service comme je
l'avais mis.

## L'IA — les états étaient mal numérotés

Répartiteur `0x010F3A` :

| État | Routine | `+$1A` |
|---|---|---|
| 0 | anticipation `0x10A02` | 1 |
| 1 | poursuite `0x10AB6` | 1 |
| 2 | **frappe** `0x10BCE` | 0 |
| 3 | **service** `0x10D44` | 1 |
| 4, 5 | immobile | — |
| 6 | recentrage `0x1096C` | 1 |
| 7 | **frappe de service** `0x10C7C` | 0 |

Les routines ne déplacent pas la raquette : elles **proposent** une position
(`$1AFCC`/`$1AFCE`) à partir de la position avant (`$1AFC8`/`$1AFCA`). Le
répartiteur ensuite :

1. ajoute un **tremblement** `alea(-t, t)` si la raquette a bougé, dans les
   états 0, 1, 2, 3 et 7 — `t` est le champ `+$4C`, que je croyais inutilisé :
   **Skip tremble de 10, Lexan de 5**, les autres pas du tout ;
2. borne à `X ∈ ±(250 − largeur/2)` et **`Y ∈ [1200, 1500]`** — la seule
   borne de la raquette adverse ; ma `contraindre()` sur la zone de patrouille
   était fausse ;
3. **pose la vitesse égale au déplacement réel** ;
4. passe en recentrage si le palet s'éloigne.

La vitesse de patrouille est **globale** (`$1AFB8`/`$1AFBA`), pas dans le bloc.

### La frappe adverse est un bond

À l'arrivée de la poursuite, la cible est retenue, et le point simulé devient
un **point d'armement** décalé de la dispersion (`+$3A`…`+$40`). La raquette
recule vers ce point ; quand `palet.y + palet.dy >= cible.y`, elle **saute sur
la cible en une image**. Sa vitesse, égale à son déplacement, devient énorme :
c'est cela qui transmet la puissance. La « dispersion » est donc le **vecteur
de frappe** — c'est pourquoi l'éditeur des auteurs la nomme
« gauche-droite / avant-arrière ».

### La simulation s'arrête à l'entrée de la zone

`0x1078E` fait avancer le palet simulé et **s'arrête dès que `Y > 1200`**.
Pendant la poursuite, elle continue d'avancer d'un pas par image : la cible
suit le palet.

### Le service adverse (état 3)

Patrouille, compte à rebours de 30 images, puis cible `(0, 1205)` et point
d'armement tiré dans `+$42`…`+$48`. **Biff** le module par l'écart au score :
`k = borner(-10, joueur - adversaire, 10) + 10`, armement `= +$44 · k / 20`.
**Bejin** tire deux bits ; le son joué dépend de celui qui fixe la direction.

### Nerual copie le joueur

Après un point où le joueur reprend le service, sa **première frappe** est
recopiée dans le bloc de Nerual (`0x010148`) : coefficients d'accélération,
et vecteur de service (`+$42`…`+$48` ← vitesse de la raquette du joueur). La
modification est durable.

### Seul Lexan joue sur une copie

`0x0106DC` : à 0-0, le bloc de Lexan est recopié dans une copie de travail
(`0x1B5B6`), sur laquelle agit l'ivresse. Les autres adversaires utilisent
directement la table.

## Le générateur aléatoire (`0x00FD94`)

```
graine = graine * 0x41C64E6D + (graine >> 20) + 0x3039
tirage = (graine >> 16) & 0x7FFF
alea(min, max) = min + reste(tirage / (max - min + 1))
```

Avec `max < min` le diviseur est négatif et le reste, du signe du dividende,
reste positif : **Skip et son `alea(34, 30)` tirent dans 34…36**. Ce n'est
pas une division par −3 comme je l'avais écrit.

## Les sons — une attribution était fausse

| Routine | Séquence | Événement |
|---|---|---|
| `$1151C` | `0x100` près, **`0x101` si Y > 750** | **frappe de raquette** — même échantillon, plus grave au fond |
| `$114E4` | `0x11A` | choc sur l'**obstacle** |
| `$11586` | `0x102` si \|dy\| > 150, sinon `0x103` | vitre : fracas ou choc sourd |
| `$115DE` | `0x200` / `0x201` | les deux services de Bejin |

J'avais écrit que `0x11A` était la frappe. `0x0102C2`, qui l'appelle, est dans
la routine de l'obstacle.

## La vitre

Treize éclats et un cadre de fissure, **tracés en lignes** (`0x00F164`),
géométrie à `$19B04` / `$19B12` / `$19BC8`. Les éclats suivent toujours la
même trajectoire (vitesse fixe, gravité +12, pas de 1/8). **C'est l'échelle du
dessin qui dépend du tir** :

```
vitre du joueur  : echelle = (150 - dy) / 4,  centre (projX(palet), 200)
vitre adverse    : echelle = (dy + 150) / 8,  centre (projX(palet), 67)
```

## Ce qui reste reconstruit dans le prototype

- la valeur initiale de `$1B584` (qui sert en premier) ;
- le passage à l'état 6 pour le lancer de Bejin, déclenché dans l'original par
  la fin d'une animation ;
- la cadence de 50 images par seconde, non mesurée ;
- l'obstacle, non transcrit ;
- la correspondance des neuf `.TC0` avec les neuf noms.

`src/ia.c` et `src/shufflepuck.c` portent encore les versions précédentes
de la détection et de l'IA : **`web/moteur.js` fait désormais foi.**

---

# L'affichage — raquettes, palet, personnages, tri

## Les sprites sont posés par le bas

`$174C8` calcule `haut = y − hauteur + 1` : le `y` qu'on lui passe est la
**ligne du bas** du sprite. Le prototype les posait par le haut, un sprite
trop bas — d'où un palet qui semblait plus proche qu'il n'était et
« traversait » la raquette. Le bit 7 de l'octet de largeur est un drapeau
(`& $7F`).

## Les raquettes sont de la 3D

`0x00DC58` : une **plaque verticale de 81 unités**, projetée par ses coins
`(x − demi, hauteur 81)` et `(x + demi, hauteur 0)`, puis tracée en
primitives — contour blanc (15), arête supérieure grise (14) épaissie à deux
ou trois lignes si `Y < 400`, contour intérieur (11), fond (12). La raquette
adverse n'est dessinée que si `+$1C` est posé : **Lexan pose sa raquette pour
boire** (`0xEFE6` l'efface, `0xEF30` la remet).

## Le palet

`0x00DE2C` choisit le sprite par **douze seuils de profondeur**
(3, 44, 92, 148, 213, 292, 389, 510, 665, 872, 1161), avec un décalage
vertical par tranche (`$1841C` : 6 5 4 4 3 2 2 1 1 1 0 0), posé par le bas en
`projY(6, y)`.

## L'ordre d'affichage (`0x00F860`)

1. le décor de la partie (`0x00D5B0`) : l'image `jeu`, une bande noire
   `y ≤ 67`, le **corps** du personnage posé le pied à 67 ;
2. découpe à `y < 68`, puis la liste de fond (`$1AF6E`, scripts en boucle)
   et les animations « derrière » (`$1AF28`, drapeau 0) — dont la **vitre du
   fond** ;
3. découpe levée : les deux **montants du fond de table** (sprites 15 et 16
   de `sprites`, en (90, 67) et (204, 67)) ;
4. raquettes et palet par ordre de profondeur (`0x00DF00`) ;
5. les animations « devant » (drapeau 1) — dont la **vitre du joueur**.

La vitre n'a pas de routine d'affichage propre : c'est un script
(`$19C98` / `$19CC0`) qui appelle les routines d'éclats. `0x00F480` le lance
en **mode 2 (devant)** pour la vitre du joueur et en **mode 0 (derrière)**
pour celle de l'adversaire.

## Les personnages

### Quel fichier pour quel adversaire

`0x00D786` choisit, par index d'adversaire, le fichier chargé et la table de
placement. L'index 1 (Vinnie) charge `visine` et l'index 2 (Visine) charge
`vinnie` — la même inversion 1↔2 que dans la table des noms. Les neuf `.TC0`
de la disquette 2, anonymes, ont été identifiés en comparant la **hauteur**
de leurs sprites à `+6` de chaque table de placement :

| index | nom | fichier | `.TC0` | concordance |
|---|---|---|---|---|
| 0 | Skip | `skip` | secteur 142 | 10/11 |
| 1 | Vinnie | `visine` | secteur 163 | 8/8 |
| 2 | Visine | `vinnie` | secteur 200 | 18/18 |
| 3 | Lexan | `lexan` | secteur 277 | 25/25 |
| 4 | Nerual | `nerual` | secteur 491 | 14/14 |
| 5 | Eneg | `general` | secteur 343 | 26/26 |
| 6 | Bejin | `bejin` | secteur 579 | 6/18 * |
| 7 | Biff | `biff` | secteur 646 | 9/9 |
| 8 | Dc3 | `droid` | secteur 65 | 7/7 |

\* seul fichier restant ; toutes ses largeurs sont compatibles.

### Le placement (`0x00F690`)

Une entrée de 8 octets par sprite : `x, y, largeur visible, hauteur`. Le
sprite 0 (le corps) est posé en `(x + 117, y + 67)`, les autres
**relativement au corps**. Avant de poser un sprite, son rectangle est effacé
en noir : les sprites d'animation sont des pièces opaques qui remplacent une
partie du corps.

### Les scripts d'animation, qui se réécrivent

`0x00F522` lance en début de partie les scripts du personnage. Une image de
script fait 10 octets : sprite A, durée, fonction de rappel, sprite B. La
durée est multipliée par 2/3. Sprite `−2` : appeler la fonction tant qu'elle
répond 1 ; `−3` : fin, puis boucle (mode 1) ou disparition.

Les fonctions de rappel **écrivent dans le script lui-même** :

- `0xED4A` (Skip), `0xEE4A` (Visine), `0xF0BE` : le personnage **suit le palet
  des yeux** — pendant la poursuite et la frappe, un sprite différent selon
  que le palet est à gauche (X < −83), au centre ou à droite ; une autre pose
  dans les autres états ;
- `0xEE0A`, `0xEE2A`, `0xF09E`, `0xF132` : une durée d'attente tirée entre 30
  et 150 — **les clignements irréguliers** ;
- `0xEEDE` (Lexan) : choisit au hasard entre deux boucles d'attente ;
- `0xEF30` / `0xEFE6` (Lexan) : font varier le `y` de son corps dans sa table
  de placement — **il se redresse ou s'affaisse derrière la table**, grâce à la
  découpe à 68 ;
- `0xF152` : passe le jeu à l'état 6. C'est la dernière image du script de
  service de Bejin (`$195BE`) : **c'est son animation qui lance le palet**.

### Une contradiction dans le code d'origine

`0x00F522` lance pour l'index 4 (Nerual) les scripts `$190C0` et `$1908E`.
Le second utilise les sprites 24 et 25, alors que le fichier `nerual` n'en a
que 14. Par leur place en mémoire — juste avant la table de `general`, comme
chaque personnage a ses scripts juste avant sa table — ces scripts semblent
être ceux d'Eneg, qui n'en reçoit aucun. Je ne tranche pas : le prototype
suit le code et ignore les numéros de sprite hors de la banque.

---

# Cadence, robot du tableau, réactions — et une erreur de lecture corrigée

## La cadence d'origine : 25 images par seconde, mesurée

La boucle n'attend pas la VBL explicitement : chaque image se termine par
l'échange d'écran (`$15AEA`, installé comme trap 5), qui bascule le tampon
puis **attend une VBL**. La cadence dépend donc du temps de calcul.

Mesure : `lexan_debut.sav` relancé dans Hatari, AVI enregistré à **chaque**
VBL (50/s) pendant 20 s de partie. Sur 992 images, l'écran change **une VBL
sur deux** dans l'immense majorité des cas (330 paliers de 2 VBL), avec
quelques paliers de 3 (16,7/s) quand l'image est plus lourde. **Le jeu tourne
à 25 images par seconde.** Le prototype, à 50, allait deux fois trop vite.

L'ancienne capture `partie.avi` ne pouvait pas trancher : elle ne contient
que l'écran-titre et le zoom d'introduction.

## Le robot du tableau (`0x00E262`)

Une main tenant une craie (sprite 0 de `sprites`) ou une éponge (sprite 27),
pilotée par la machine à états `$18438`, en tête du rendu de chaque image :

| état | |
|---|---|
| 0 | repos, cachée ; `$E182` compare scores réels et scores affichés |
| 1 | glisse en X vers la colonne du prochain bâton, 5 px par image |
| 2 | puis en Y vers la ligne (joueur à 10, adversaire à 21) |
| 3 | trace le bâton : 3 pas de 2 px, ou 4 pas (+4, +1) pour le 5e en diagonale |
| 4 | redescend jusqu'à Y = 90 |
| 5 | sort par la gauche jusqu'à X = −60, puis se cache |
| 6, 7 | l'éponge, aller puis retour, quand un score a **baissé** |

Colonne du n-ième bâton (`$DFEC`) : `x = (n/5)·18 + 36`, puis `+4·(n%5)+1`, ou
`−16` pour le cinquième. La pointe de la craie est en `(X + 48, Y − 45)`.

Les bâtons sont tracés dans le **décor** (`$1B52E`) : ils persistent.
L'éponge recopie le tableau vierge par bandes de 4 lignes. La routine de copie
de blocs `$17A5A` prend la **source en premier** — établi par cohérence entre
trois appels.

Le tableau lui-même est le sprite 1 de `sprites` (112×31), posé en (0, 30),
avec « Visiteur » en (5, 9) et le nom de l'adversaire en (5, 20).

## Les réactions et les voix (`0x00F998`)

Chaque adversaire a une table de cinq scripts, lancés en mode 0 au point :
0 point quelconque, 1 le joueur gagne, 2 le joueur marque, 3 l'adversaire
marque, 4 l'adversaire gagne. Le tirage est **le même** que celui de
l'ivresse de Lexan.

Les fonctions de rappel de ces scripts jouent des sons (`$112C0`), sous deux
formes seulement : une suite de sons fixes, ou un tirage `rand % 3` entre trois
répliques. L'exporteur les **reconnaît au désassembleur** plutôt que de les
recopier : 20 fonctions reconnues ; les autres sont exactement celles
transcrites à la main.

## Erreur corrigée : les index 4 et 5

J'avais lu les cas de `0x00D786` **dans l'ordre du listing**, sans décoder sa
table de saut. Décodée, elle envoie **l'index 4 (Nerual) sur `general`** et
**l'index 5 (Eneg) sur `nerual`**. La « contradiction » signalée plus haut
entre `D786`, `F522` et `F998` n'existait pas : les trois routines sont
cohérentes, c'était ma lecture qui ne l'était pas. Deux personnages étaient
inversés dans le prototype.

## Un désaccord ouvert : la vitre du fond

D'après le code, les éclats de la vitre du fond sont tracés **après** le
personnage : leur script est dans la liste « derrière » (`$1AF28`), qui passe
après la liste de fond et après le corps, et la routine de ligne (`$16EBE`)
écrit ses pixels sans condition. Ils passent donc **devant** le personnage,
sous les raquettes, coupés au bord de la table. Fabien se souvient de les voir
passer derrière. À vérifier sur une capture d'un point marqué.
