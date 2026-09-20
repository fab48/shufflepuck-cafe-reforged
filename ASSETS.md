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
soixante entrées de pur bruit. Aucune chaîne `SPRITES`, `BARSPRIT`, `INTBAR`
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
