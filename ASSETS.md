# Extraction des graphismes

## Format

Basse résolution Atari ST : **320×200, 4 plans de bits entrelacés par mots de 16 bits,
16 couleurs**. Palette de 16 mots `$0RGB` (3 bits par composante sur STF).

`tools/stgfx.py` décode ce format et exporte en PNG. Validé sur l'écran-titre.

## Emplacements en mémoire

| Adresse | Contenu |
|---|---|
| `$01B53E` | **palette**, 16 mots — juste avant l'écran |
| `$01B700` | **tampon d'affichage**, 32000 octets |
| `$0F8000` | **second tampon** (double buffering) — profil identique au premier |

Le second tampon est confirmé par la mesure : écart moyen entre octets voisins de 62,9
contre 64,0 pour l'écran-titre, et 52 % de petits écarts contre 51 %. Même nature.

## ⚠️ Les graphismes sont compressés

Trois hypothèses testées et **toutes réfutées** :

| Hypothèse | Test | Résultat |
|---|---|---|
| plans de bits en clair dans la banque `$4C000` | corrélation entre lignes | 34 % contre 70 % pour un vrai écran — **non** |
| échantillons sonores | écart moyen entre octets voisins | profil de code, pas de signal continu — **non** |
| zones chargées au match `$61000`, `$63000` | corrélation entre lignes | 24 % et 21 % — **non** |

Aucune image en clair n'existe ailleurs que dans les deux tampons d'affichage. Le jeu
décompresse directement à l'écran.

### Limite de la mesure
La corrélation entre lignes ne distingue pas « image structurée » de « données très
répétitives » : un bloc quasi constant donne 90 %. Elle sert à **réfuter**, pas à
confirmer.

## Méthode d'extraction retenue

**Capturer l'écran**, seul endroit où l'image est en clair.

### Par instantané mémoire
`F12` → *Memory* → *Save*, puis décoder `$01B700` avec la palette `$01B53E` :

```
python tools/extraire_ecran.py <fichier.sav> <sortie.png>
```

### Par Hatari directement
`Alt+G` écrit le framebuffer natif en PNG, sans bordure ni mise à l'échelle,
dans `work/captures/`. Configuré dans `run/jouer.bat` (`bCrop = TRUE`).

## Ce qu'il faut capturer

Une passe complète de jeu, en capturant à chaque écran nouveau :

- écran-titre, café, tableau des scores
- la table, à vide et en jeu
- **chaque adversaire** : posture normale, victoire, défaite, animations
- la vitre brisée, le bras robotisé du tableau de score

C'est la seule voie pour obtenir la totalité des images sans écrire un
décompresseur — lequel supposerait d'identifier puis de rétro-ingénierer
l'algorithme de compression du jeu.

---

# Les fichiers d'origine, récupérés depuis les disquettes

*21 septembre 2026*

Jusqu'ici les images venaient de la mémoire du jeu ou de captures d'écran.
Ce sont désormais **les fichiers d'origine**, lus sur les disquettes.

## Aucune des deux disquettes n'a de système de fichiers

`tools/stx_image.py` reconstruit une image brute depuis le conteneur Pasti.
Les deux disquettes se lisent intégralement — **720 secteurs, aucun manquant** —
et leur secteur d'amorçage porte un BPB parfaitement cohérent : 512 o/secteur,
2 secteurs/cluster, 2 FAT de 5 secteurs, 112 entrées de répertoire, 720 secteurs.

Mais c'est un leurre. La FAT est blanchie (`F7 FF FF` puis des zéros : tout
libre) et le répertoire ne contient aucun nom. `tools/fat12.py` en sort
soixante entrées de pur bruit *(outil retiré lors du ménage de septembre 2026 ; il reste dans l'historique git)*. Aucune chaîne `SPRITES`, `BARSPRIT`, `INTBAR`
ni `.PC1` n'existe nulle part sur les deux disquettes.

**Le jeu lit donc par secteur absolu.** On ne peut pas demander la liste des
fichiers. On peut en revanche reconnaître leur forme.

## Les images sont au format Degas Elite `.PC1`

Le chargeur à `0x015684` compose un nom de fichier puis l'ouvre :

    015684  link  a5, #-$3C
    015688  move.l $8(a5), -(a7)     ; nom de base
    01568c  pea    -$14(a5)
    015690  jsr    $18136            ; strcpy
    015698  pea    $1573e(pc)        ; ".PC1"
    0156a0  jsr    $18248            ; strcat
    0156a8  clr.w  -(a7)             ; mode lecture
    0156ae  jsr    $16d2e            ; Fopen

et juste au-dessus, à `0x01565C`–`0x015680`, se trouve sa boucle de
décompression : une copie littérale `move.b (a0)+,(a1)+ / dbra` et une
répétition `move.b d2,d1 / move.b d1,(a1)+`. C'est **PackBits**, exactement
le format Degas Elite.

Ce n'est donc pas un schéma maison : c'est un format documenté.

`tools/trouver_pc1.py` cherche la signature et la **vérifie** :

- en-tête `$8000` (basse résolution, compressé) ;
- 16 mots de palette valides (`w & $F888 == 0`) ;
- et surtout : la décompression doit rendre **exactement 32 000 octets**.

Ce dernier critère est décisif. Une suite d'octets quelconque ne se
décompresse pratiquement jamais sur la taille exacte d'un écran ST.

## Le piège de l'agencement

La sortie PackBits n'est pas de la mémoire écran. Degas range chaque ligne
**plan par plan** — 40 octets du plan 0, puis 40 du plan 1, etc. — alors que
l'écran ST **entrelace** les plans par mots de 16 bits. Rendue telle quelle,
l'image donne un bruit coloré qui ressemble à une image cassée, ce qui est
trompeur : on croit à une erreur de décompression alors que celle-ci est
juste. `stgfx.degas_vers_ecran()` fait le réentrelacement.

## Ce qui a été récupéré

| Disquette | Secteur | Compressé | Contenu |
|---|---:|---:|---|
| 1 | 136 | 8 645 o | « Brøderbund Software Presents » (trois couronnes) |
| 1 | 153 | 24 544 o | Écran-titre |
| 1 | 505 | 14 699 o | **Le terrain en perspective** |
| 1 | 632 | 8 792 o | « Tableau des Maîtres » (meilleurs scores) |
| 1 | 650 | 30 790 o | « Current Champion » (galerie des personnages) |
| 2 | 4 | 30 790 o | idem, dupliqué sur la disquette 2 |

Les `.pc1` d'origine et les `.png` rendus sont dans `work/assets/pc1/`.

## Ce que l'écran-titre apprend

Les crédits lèvent une ambiguïté sur les noms des adversaires :

> by Christopher Gross — additional design contributions by
> **Gene Portwood**, **Lauren Elliott**, Infogrames —
> © Copyright 1989 Brøderbund Software, Inc. — V1.0

**Eneg** est *Gene* à l'envers et **Nerual** est *Lauren* à l'envers. Ce sont
les concepteurs eux-mêmes. Ce n'est plus une supposition sur des noms
bizarres : c'est écrit dans le générique.

## Ce qui manque encore

Six écrans, c'est le décor fixe. Il manque tout l'animé : le café, les neuf
adversaires, les raquettes, le palet, le bris de verre. Ces éléments sont
dans les autres formats que le binaire nomme — **`.TC0`**, **`.CPL`**, et les
fichiers `sprites` / `barsprit` chargés depuis `0x00D212` et `0x00D224`.
Leurs chargeurs sont identifiés mais leurs formats ne sont pas résolus.

---

# L'audio numérisé, récupéré et converti

## Comment un STF joue du son numérisé sans DMA

Le STF n'a pas de canal audio DMA — c'est le STE qui l'apporte. Shufflepuck
joue pourtant des sons numérisés. Le mécanisme, établi entièrement par
lecture du code :

Le gestionnaire du **Timer A du MFP** (vecteur `$134`, routine `0x014240`)
consomme **un octet par tic** dans un flux, et s'en sert comme **index dans
une table de 256 entrées à `0x014296`**. Chaque entrée porte trois paires
registre/valeur écrites d'un coup au YM2149 par `movep` :

    014246  movea.l #$3b578, a0        ; curseur courant
    01424e  move.b  (a0)+, d0          ; un octet du flux
    014250  beq     $1427c             ; zéro = fin
    014252  move.l  a0, $14248.l       ; réécrit son propre opérande
    014258  lea     $8800.w, a0        ; le YM2149
    01425c  lsl.w   #$3, d0            ; index x 8
    01425e  move.l  $14296(pc, d0.w), d1
    014262  move.w  $1429a(pc, d0.w), d0
    014266  movep.l d1, $0(a0)         ; (R8,v) (R9,v)
    01426a  movep.w d0, $0(a0)         ; (R10,v)

Les registres 8, 9 et 10 du YM2149 sont les **volumes des trois voies**. Le
jeu module donc les trois volumes à la fréquence d'échantillonnage : trois
convertisseurs de 4 bits combinés donnent une résolution proche de 8 bits.

Le code est **auto-modifiant** : `0x014252` réécrit l'opérande immédiat de
`0x014246`. C'est ce qui fait tenir le gestionnaire en une poignée
d'instructions.

## Ce que les octets signifient, et comment on le sait

La table fait **exactement 256 entrées de 8 octets**, toutes de la forme
`(R8=v1, R9=v2, R10=v3)` — une par valeur d'octet possible. C'est déjà
dirimant : il s'agit d'une conversion octet → amplitude.

Restait à savoir dans quel sens. Trois modèles ont été mis en concurrence
en ajustant par moindres carrés une courbe de DAC à 15 inconnues
(`f(0)=0`, `f(1)`…`f(15)` libres), sur les 256 équations
`f(v1)+f(v2)+f(v3) = cible` :

| modèle | erreur moyenne |
|---|---:|
| amplitude ∝ **(127 − octet signé)** | **2,4 %** |
| amplitude ∝ (octet signé + 128) | 5,3 % |
| amplitude ∝ \|octet signé\| | 17,8 % |

Et la courbe reconstituée a des rapports successifs groupés autour de
**1,4** — soit 3 dB par pas, la signature documentée du YM2149.

**Les échantillons sont donc du PCM signé 8 bits, stocké inversé.**

## Format d'une banque `.ECH`

Lu dans le chargeur `0x014B64` :

    +$00  mot    N1   nombre d'échantillons
    +$02  mot    N2   nombre de séquences
    +$04  long[] table d'offsets relatifs au début du fichier

    table[1..N2]     -> les séquences
    table[N2+1]      -> sautée
    table[N2+2...]   -> les échantillons ; longueur = différence avec le suivant

Une **séquence** est une suite de paires `(numéro d'échantillon, TADR)`
terminée par `$FF`. `TADR` est le diviseur du Timer A. Le stub d'armement
à `0x014176` pose `TACR = 1`, soit un prescaler de **4**, d'où :

    fréquence = 2 457 600 / (4 x TADR)

## Ce qui a été extrait

Banque trouvée sur la disquette 1, secteur 201, 141 053 octets.

| # | Octets | TADR | Fréquence | Durée |
|---|---:|---:|---:|---:|
| 0 | 39 795 | 60 | 10 240 Hz | 3,89 s |
| 1 | 59 098 | 58 | 10 593 Hz | 5,58 s |
| 2 | 26 505 | 87 | 7 062 Hz | 3,75 s |
| 3 | 15 528 | 67 | 9 170 Hz | 1,69 s |
| 4 | 7 | 60 | — | (bouchon) |

Contrôle de vraisemblance : les quatre se centrent sur 127,0–127,3 (centre
exact d'un 8 bits non signé), occupent toute la plage 0–255, et présentent
5 % à 26 % de passages par le centre. C'est du signal audio, pas du bruit.

`work/assets/wav/` — `tools/extraire_ech.py`.

## Ce qui reste

Le binaire nomme **deux** banques, `ringard.ech` et `shuffle.ech`, et une
seule a été trouvée. La seconde est soit ailleurs sur la disquette 1 sous
une forme que la signature ne reconnaît pas, soit absente de ce tirage.

---

# Les sprites : `.CPL` et `.TC0`

## Le manifeste de chargement

La séquence `0x00D190`–`0x00D290` charge tous les décors et dit quel
format va avec quel fichier :

| Fichier | Format | Chargeur | Contenu |
|---|---|---|---|
| `BRODER` | `.PC1` | `0x152D4` | les trois couronnes Brøderbund |
| `PRESENT` | `.PC1` | `0x152D4` + `0x153AE` | l'écran « Presents » et sa palette |
| `jeu` | `.PC1` | `0x15684` | **le terrain en perspective** |
| `barsprit` | `.CPL` | `0x15294` | les sprites du bar |
| `sprites` | `.CPL` | `0x15294` | les sprites |
| `quete.fnt` | brut | `0x150A0` | la fonte |
| `INTBAR` | `.PC1` | `0x153AE` | l'intérieur du bar et sa palette |

Et ailleurs, `0x00D56E` appelle le chargeur `.TC0` avec un **nom
dynamique** — celui que choisit la table de saut à `0x00D7DE`, qui égrène
`skip`, `visine`, `vinnie`, `lexan`, `nerual`, `general`, `bejin`,
`biff`, `droid`. **Les `.TC0` sont les neuf adversaires.**

## `.CPL` — un RLE à convention inversée

Décompresseur à `0x015116`. En-tête de deux mots (taille compressée,
taille décompressée), puis un flux à octet de contrôle dont la convention
est **l'inverse de PackBits** :

    c <  $80 : répéter c fois l'octet suivant     (consomme 2)
    c >= $80 : copier (c & $7F) octets littéraux  (consomme 1 + n)

Sans le « +1 » de Degas. Un compteur nul existe donc et ne produit rien.

## `.TC0` — codage par paires d'octets

Décompresseur à `0x01554A`. Le chargeur charge le compressé **à la fin**
du tampon de sortie et décompresse en place — une économie d'allocation
qui ne laisse aucun tampon intermédiaire.

Le fichier se découpe en blocs :

    +$00  octet  N, nombre de paires (0 = bloc non compressé)
    +$01  octet  drapeau : non nul s'il reste des blocs
    +$02  mot    nombre d'octets du bloc, en PETIT-BOUTISTE
    puis, si N ≠ 0 : N symboles, N premiers octets, N seconds octets

Certaines valeurs d'octet sont des symboles qui se développent en deux
autres octets, eux-mêmes développables. L'expansion est récursive mais
déroulée sur la pile, avec deux zéros empilés comme marqueur de fond.
Quand plusieurs paires partagent un symbole, une liste chaînée les relie
et le code retient la dernière dont l'index est **inférieur** à l'index
courant — c'est ce qui interdit les cycles.

`tools/tc0.py` est une transcription instruction par instruction : les
états y portent les adresses d'origine (`L15650`, `L1562C`, `L15640`,
`L15668`). Ce n'est pas une reconstruction d'après l'idée générale, et
c'est délibéré : une première version « comprise plutôt que transcrite »
avait inversé la comparaison `cmp.b (a3,d2.w),d0 / bhi` et perdait 15 %
des octets en silence, sans jamais planter.

## Structure commune des banques de sprites

`.CPL` et `.TC0` décompressent vers la même chose : une table de
pointeurs en tête, puis les sprites.

    +$00  long[]  offsets ; le premier donne la taille de la table
    à chaque offset :
    +$00  octet   largeur en mots de 16 pixels
    +$01  octet   hauteur en lignes
    +$02  ...     largeur x hauteur x 4 plans x 2 octets

Validation : la taille déduite de l'en-tête doit égaler l'écart entre
deux offsets consécutifs. Trois autres conventions testées (en-tête de 4
ou 6 octets, plan de masque supplémentaire) donnent 0 sur 57 ; celle-ci
donne **57 sur 57** — et 100 % sur les neuf banques d'adversaires.

Un `.TC0` porte **deux** parties : la partie 1 est la banque de sprites,
la partie 0 un second conteneur à deux compteurs, non résolu.

## Ce qui a été extrait

**`barsprit.CPL`** — disquette 1, secteur 534 : 57 sprites (visages des
clients du bar, yeux qui clignent, enseignes « EXIT », mains).

**Les neuf `.TC0`** — disquette 2, qui était inexpliquée à 91 % :

| Secteur | Compressé | Décompressé | Sprites |
|---:|---:|---:|---:|
| 65 | 39 075 | 51 858 | 7 |
| 142 | 10 526 | 14 648 | 11 |
| 163 | 18 741 | 25 652 | 8 |
| 200 | 38 938 | 53 558 | 18 |
| 277 | 33 419 | 48 598 | 25 |
| 343 | 75 346 | 88 936 | 26 |
| 491 | 44 817 | 55 866 | 14 |
| 579 | 34 227 | 48 864 | 18 |
| 646 | 29 297 | 37 908 | 9 |

**Neuf fichiers, neuf adversaires, 136 sprites d'animation.** Le compte
tombe juste tout seul, ce qui est la meilleure confirmation possible.

Planches dans `work/assets/png_tc0/`. La palette employée est celle du
terrain ; chaque adversaire a probablement la sienne, vraisemblablement
dans la partie 0 non résolue.

---

# La seconde banque sonore, et ce qu'elle tranche

`tools/trouver_ech.py` ne trouvait qu'une banque sur les deux annoncées
par le binaire. La cause était un défaut du balayage, pas du format :
après une trouvaille, il avançait de la longueur du fichier — 141 053
octets, **impaire**. Tous les offsets suivants étaient impairs, et la
seconde banque, alignée sur un secteur, n'était jamais testée. Les trois
scanners balaient désormais secteur par secteur.

Seconde banque : disquette 1, secteur 477, 13 483 octets, **5
échantillons et 28 séquences**.

## Le rebond du palet est transposé, pas réenregistré

| Séquence | Échantillon | TADR | Fréquence |
|---:|---:|---:|---:|
| 0 | 1 | 84 | 7 314 Hz |
| 1 | 1 | 108 | 5 688 Hz |
| 2 | 0 puis 3 | 69 | 8 904 Hz |
| 3 | 3 | 61 | 10 072 Hz |
| **4 à 26** | **2** | **44 … 164** | **13 963 … 3 746 Hz** |
| 27 | 4 | 48 | 12 800 Hz |

Les séquences 4 à 26 jouent **toutes le même échantillon** — un clic de
1 275 octets, 0,09 s — à vingt-trois hauteurs différentes, TADR croissant
44, 46, 49, 52, 55, 58, 61, 65, 69, 73, 77, 81, 85, 89, 93, 98, 103,
108, 113, 118, 124, 130, 164.

Cela ferme une question restée ouverte. J'avais relevé dans le binaire
« vingt-deux rebonds partageant leur premier octet et ne différant que
par une valeur montant de 44 à 130 », sans savoir ce qu'était ce second
octet. C'est le **diviseur du Timer A** : le premier octet désigne
l'échantillon, le second la fréquence de relecture.

Le ST transpose donc bel et bien — en changeant le diviseur du timer. Le
jeu n'a pas vingt-deux sons de rebond enregistrés : il en a **un**, joué
à vingt-trois vitesses selon la profondeur de l'impact.

Et cela valide les constantes déjà établies dans `PHYSICS.md` :
`SP_SON_REBOND_BASE = 4` et la bande choisie par `Y / 68` désignent bien
les séquences 4 à 25 de cette banque.

## `sprites.CPL` — l'interface et le palet

Second `.CPL`, disquette 1 secteur 607 : 11 728 → 18 736 octets,
**28 sprites**.

    64x46   une main
    112x31  le schéma du terrain
    128x19  le logo « Shufflepuck »
    32x25  32x22  32x19  32x17  32x15  32x12  32x11
    16x9   16x7   16x6   16x4
    puis les boutons « CANCEL » et « EXIT », les barres d'interface

La suite décroissante de onze tailles, c'est **le palet mis à l'échelle
en perspective**, pré-rendu à chaque profondeur. Quatorze tailles de
palet, vingt-trois hauteurs de rebond : la profondeur est quantifiée
dans l'image comme dans le son.

---

# Cartographie complète des deux disquettes

`tools/carte_disque.py` passe chaque secteur au crible des quatre
signatures et **vérifie** chacune par une égalité de taille. Ce qui
reste après cela est ce qu'on ne sait pas encore lire — et c'est le seul
chiffre qui compte.

## Disquette 1

| Secteurs | Octets | Contenu |
|---|---:|---|
| 0–135 | 69 632 | **le programme** (code 68000, tables de saut, table des volumes YM) |
| 136–152 | 8 645 | `.PC1` — « Brøderbund Software Presents » |
| 153–200 | 24 544 | `.PC1` — écran-titre |
| 201–476 | 141 053 | `.ECH` — 5 échantillons, 5 séquences (la musique) |
| 477–503 | 13 483 | `.ECH` — 5 échantillons, 28 séquences (les bruitages) |
| 505–533 | 14 699 | `.PC1` — `jeu`, le terrain en perspective |
| 534–606 | 36 945 | `.CPL` — `barsprit`, 57 sprites |
| 607–629 | 11 732 | `.CPL` — `sprites`, 28 sprites (interface et palet) |
| 632–649 | 8 792 | `.PC1` — tableau des maîtres |
| 650–710 | 30 790 | `.PC1` — « Current Champion » |

Reste : 8 325 octets, soit **2 %** — des queues de fichier entre deux
frontières de secteur, plus 5 050 octets en fin de disquette dont la
nature n'est pas établie.

## Disquette 2

| Secteurs | Octets | Contenu |
|---|---:|---|
| 4–64 | 30 790 | `.PC1` — « Current Champion », dupliqué |
| 65–141 | 39 083 | `.TC0` — adversaire, 7 sprites |
| 142–162 | 10 534 | `.TC0` — adversaire, 11 sprites |
| 163–199 | 18 749 | `.TC0` — adversaire, 8 sprites |
| 200–276 | 38 946 | `.TC0` — adversaire, 18 sprites |
| 277–342 | 33 427 | `.TC0` — adversaire, 25 sprites |
| 343–490 | 75 354 | `.TC0` — adversaire, 26 sprites |
| 491–578 | 44 825 | `.TC0` — adversaire, 14 sprites |
| 579–645 | 34 235 | `.TC0` — adversaire, 18 sprites |
| 646–703 | 29 305 | `.TC0` — adversaire, 9 sprites |

**96 % identifié.** Reste 13 392 octets : les queues de fichier, le
secteur d'amorçage leurre, et 8 583 octets en fin de disquette.

## Ce qui n'a pas été trouvé

Le manifeste charge un fichier **`INTBAR.PC1`** — l'intérieur du bar —
et une fonte **`quete.fnt`**. Ni l'un ni l'autre n'existe sur les deux
disquettes : aucun en-tête `$8000` ailleurs qu'aux cinq images
recensées, même en relâchant le test de palette aux seize couleurs STE,
et aucune image Degas non compressée nulle part.

Je le note comme un fait, pas comme un échec de recherche : le code qui
les charge est atteignable, mais les fichiers ne sont pas là. Soit ce
tirage ne les contient pas, soit ils sont produits autrement.

---

# Chaque adversaire a sa voix

Un `.TC0` porte deux parties. La partie 1 est la banque de sprites. La
partie 0, qui restait non résolue, est une **banque sonore au format
`.ECH` exactement** : deux compteurs, une table d'offsets, N2 séquences
de paires (échantillon, TADR) terminées par `$FF`, puis N1 échantillons.

Les neuf fichiers contiennent donc, chacun, les images **et la voix** de
leur personnage. C'est ce qui explique leur taille.

Le premier est le plus bavard — 11 échantillons, 10 séquences, et
plusieurs séquences enchaînent trois ou quatre échantillons à des
hauteurs légèrement différentes pour composer une réplique :

    séquence 1 : #0@9035Hz + #1@9035Hz + #2@9035Hz
    séquence 4 : #2@9752Hz + #3@8777Hz + #6@9035Hz + #7@9035Hz
    séquence 8 : #8@9752Hz + #3@8777Hz + #6@9035Hz + #2@9035Hz
    séquence 9 : #10@10240Hz          (1,72 s — la plus longue)

Le même échantillon revient dans plusieurs séquences, à des hauteurs
différentes : le jeu compose ses répliques par recombinaison, exactement
comme il compose ses rebonds par transposition.

**33 fichiers WAV extraits**, dont 32 passent le contrôle de
vraisemblance (centrés sur 127, dynamique pleine, 10 à 56 % de passages
par le centre). `work/assets/voix/` — `tools/extraire_voix.py`.
