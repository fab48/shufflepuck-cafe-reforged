# Shufflepuck Café (Atari ST, Loriciel/Brøderbund) — journal de rétro-ingénierie

> **Règle du projet.** Aucune affirmation sans les octets en face. Toute ligne non
> accompagnée d'une preuve est une hypothèse et doit être étiquetée comme telle.
> Les sections « ⚠️ non vérifié » sont des pistes, pas des acquis.

## Source

Jeu d'origine possédé par l'utilisateur (STF), dumpé au niveau flux.
Répertoire : `C:\shufflepuck_café_brøderbund_software_loriciel\`

| Format | Rôle |
|---|---|
| `.scp` | flux SuperCard Pro, ~26 Mo/disquette — master d'archivage |
| `.hxcstream` | flux brut HxC, 83 fichiers (1/piste) — second format, indépendant |
| `.stx` | Pasti — lisible nativement par Hatari, protection incluse |
| `.hfe` | prêt pour Gotek sur machine réelle |
| `.bmp` | scans d'étiquettes |

Deux disquettes, **face 0 uniquement** → simple face 360 Ko, d'où la publication en
deux volumes.

## ✅ Vérifié

### Conteneur Pasti
Les deux `.stx` : magic `RSY\0`, version 3, **83 pistes**, révision 2, **zéro fuzzy byte**
sur l'intégralité des deux disquettes. La protection n'est donc pas à base de bits
instables — c'est structurel, la variante la plus simple à traiter.

Pistes 80/81/82 à 0 secteur = débordement volontaire du dumpeur au-delà des 80 pistes
standard, non formaté.

### Répartition des secteurs
```
Disquette 1 : {0 secteur: 3 pistes, 9 secteurs: 79 pistes, 70 secteurs: 1 piste}
Disquette 2 : {0 secteur: 3 pistes, 9 secteurs: 80 pistes}
```
→ **La disquette 2 n'est pas protégée.** Géométrie entièrement standard.

### La protection : piste 79, face 0
```
70 secteurs, flags=0x0061, mfm=6247, taille du record = 43 226 o (vs ~10 500 normal)
70 ID distincts, tous de taille 2 (=512 o)
ID (piste,tête,secteur,taille) : (79,0,0,2) (79,0,5,2) (79,0,10,2) (79,0,15,2) ...
```
Numérotation par pas de 5. 70 × 512 = 35 840 octets déclarés sur une piste qui en
contient physiquement ~6 250 en MFM → **secteurs fantômes chevauchants**. Énumérables
par le contrôleur, non reproductibles par un copieur secteur. Piste 79 = dernière
piste, emplacement canonique d'une piste-clé.

### Disquette 1 — secteur d'amorçage
```
60 70 00 00 00 00 00 00 7e 58 00 00 02 02 01 00 02 70 00 d0 02 f8 05 00 09 00 01 00 00 00 4d fa
```
Décodage du BPB : 512 o/secteur · 2 secteurs/cluster · 1 réservé · 2 FAT ·
112 entrées racine · 720 secteurs · média 0xF8 · 5 secteurs/FAT · 9 secteurs/piste ·
**1 tête**. Offset 30 : `4d fa` = début du code 68000.

**Somme de contrôle = 0x1234** → secteur exécuté au boot par le ROM de l'ST.

### Disquette 1 — pas de système de fichiers
Aux emplacements imposés par le BPB on trouve du 68000, pas des structures FAT :
```
secteur logique 1  (FAT1)   : 30 3b 00 d6 4e fb 00 00   MOVE.W (d6,PC,D0.W),D0 / JMP (PC,D0.W)
secteur logique 6  (FAT2)   : 4e b9 00 00 28 f0         JSR $28F0
secteur logique 11 (racine) : ba 7c 01 fe 6c 04 78 07   CMPA.W #$01FE,A5 / BGE.S / MOVEQ #7,D4
```
Le BPB n'est présent que pour satisfaire le ROM. **Le disque est un chargeur maison
suivi de données brutes adressées par secteur.** Les graphismes ne sont donc pas
dans des fichiers : il faudra comprendre le chargeur pour les localiser.

### Disquette 2 — BPB
```
boot[0:16] : 00 00 4e 4e 4e 4e 4e 4e 11 a4 2f 00 02 02 01 00
```
Pas de branchement en tête, somme de contrôle 0x844d → **non bootable**, cohérent avec
une disquette de données. BPB identique en géométrie à la disquette 1 (média 0xF9).
FAT1 (secteur logique 1) commence par `f7 ff ff 00 00 ...`. Les 32 derniers Ko sont à
87 % de `0xE5` = remplissage de formatage vierge.

## 🐛 Bug ouvert — lecteur Pasti maison

`tools/stx_sectors.py` lit correctement les secteurs ordinaires mais **se trompe sur
ceux dont les données résident à l'intérieur de l'image de piste** (descripteurs dont
l'offset pointe sous `track_image_size` — ex. piste 0 secteur 4, `off=2176` pour une
image de 6247 o).

Preuve du défaut : sur la disquette 2, FAT1 sort correctement (`f7 ff ff`) alors que
FAT2, qui doit en être la copie conforme, sort autre chose. Le répertoire racine est
donc faux par la même cause.

**Décision : ne pas persévérer sur un lecteur Pasti écrit à la main.** Hatari embarque
une implémentation correcte et éprouvée (`floppy_stx.c`). S'appuyer dessus.

Les images `work/disk*.partial.st` portent le suffixe `partial` pour cette raison :
**secteur 0 fiable, le reste non.** Ne pas les utiliser comme source de vérité.

## ⚠️ Non vérifié

- Contenu réel de la disquette 2 (bloqué par le bug ci-dessus).
- Rôle exact de la piste 79 dans le chargeur : quand est-elle lue, que teste-t-elle ?
- Format des graphismes (plans de bits ST attendus, 320×200×16, mais non constaté).
- Emplacement des données dans les secteurs bruts de la disquette 1.

## Pistes écartées

- **Recompiler pour l'ST après upscale des graphismes.** Impossible : le Shifter plafonne
  à 320×200 en 16 couleurs. Aucun mode ne permet d'afficher des assets agrandis.
- **Bâtir le remaster sur la version ST.** La version Macintosh dispose d'un fork de
  ressources propre (187 `PICT` QuickDraw 1 bit, format documenté) là où l'ST n'a
  aucun système de fichiers. Le remaster ira sur la base Mac ; l'ST reste la version
  qu'on fait tourner à l'authentique.

## Extraction de la RAM depuis un instantané Hatari

Instantané pris en match contre Skip (`work/dump/skip2.sav`), gzip, 4 346 389 octets
décompressés — il contient la RAM, la ROM TOS et les deux images disque.

### Pourquoi les repères habituels échouent
`phystop` ($42E), `_sysbase` ($4F2), les valeurs magiques ($752019, $237698AA,
$5555AAAA) et la table des vecteurs d'exception sont **tous absents ou écrasés**.
Le jeu prend la machine entière, TOS compris, et réutilise la mémoire basse.
Maximum observé sur la table des vecteurs : 8 sur 62.

### Ce qui marche : le code se référence lui-même
550 instructions `JSR` en adressage absolu long (`4E B9`) donnent une cartographie
directe :

```
cibles ST : 0x008d3e .. 0x018248   -> ~64 Ko de code
JSR dans le fichier : 0x00cc55 .. 0x017e45
```

**Carte mémoire du jeu en cours d'exécution :**
- code : ST 0x008000 – 0x018300 environ
- variables / données : au-dessus de 0x018000 (ex. `$1AF1C` lu par le code)

### Vérification : c'est bien du 68000
Extrait à 0x00f009 dans la RAM extraite :
```
4e 55 00 00      LINK    A5,#0
48 e7 0e 20      MOVEM.L D4-D6/A2,-(SP)
36 39 0001af1c   MOVE.W  $0001AF1C,D3
48 c3            EXT.L   D3
87 fc 0005       DIVS    #5,D3
48 43            SWAP    D3
```
Prologue de fonction, lecture d'une variable globale, division par 5. Code valide,
sans ambiguïté.

### ⚠️ Base non définitive
La base retenue est 0x1ee, mais le critère utilisé (« l'opcode n'est ni 0000 ni FFFF »)
est faible : avec 30 % de remplissage, beaucoup d'octets quelconques le passent.
Indice contradictoire : des chaînes de configuration Hatari se trouvent à 0x62d–0xc57
du fichier, ce qui les placerait dans la zone des variables système si la base était
0x1ee. La vraie base est probablement juste après l'en-tête de configuration (~0xd5c).

**Incertitude : quelques kilo-octets.** Sans effet sur le désassemblage — le code se
lit correctement — mais à corriger dans Ghidra, où la cohérence des références
absolues tranchera immédiatement.

## Base mémoire des instantanés : 0x000F95 (résolu)

### La méthode qui marche
`--parse` avec un point d'arrêt conditionnel **sur un démarrage normal** (pas avec
`--memstate`, qui neutralise les points d'arrêt) :

```
setup.txt    : b VBL > 2500 :once :file on_break.txt
on_break.txt : savebin loaded.ram 0 $100000
               cont
```
Chemins **relatifs obligatoires** : l'option `:file` coupe au premier `:`, donc
`D:\...` est lu comme le fichier « D ». Lancer Hatari depuis le dossier de travail.

Le dump obtenu a l'adresse ST 0 à l'offset 0 — **base vraie par construction**.

### Calibrage des instantanés
Six empreintes de 64 octets prélevées dans `loaded.ram` à des adresses ST connues,
recherchées dans les `.sav` décompressés. **Les six donnent 0x000F95**, dans les trois
fichiers.

### Cause de tous les échecs précédents
J'avais retenu 0x1EE — faux de 3 495 octets. Les valeurs que j'attendais étaient
elles-mêmes erronées :

| Variable | Ce que j'attendais | Valeur réelle |
|---|---|---|
| `_sysbase` ($4F2) | 0x00FC0000 | **0x00000940** |
| `memvalid` ($420) | 0x00752019 | **0x752019F3** |
| `v_bas_ad` ($44E) | — | **0x0001B700** |
| `phystop` ($42E) | 0x00100000 | 0x00100000 ✓ |

Une correspondance isolée de `phystop` sur 4,3 Mo balayés tous les 2 octets est
**statistiquement attendue**, pas significative. J'ai conclu avant de calculer.

## Carte mémoire vérifiée

```
0x008D3E – 0x018248   code        (550 JSR absolus ; 441/550 cibles sur
                                   LINK A5 / LINK A6 / MOVEM.L = 80 %)
0x018300 – 0x01B6FF   données
0x0001B700            base écran
0x000F8000            _memtop
0x0106A2              table des noms d'adversaires ("Skip", "Biff" à +0x30)
0x00E132              chaîne "Visiteur"
```

## Variables candidates

34 adresses sont **référencées par le code ET modifiées** entre les deux impacts
aux coins opposés (bas-gauche / haut-droite), captures fournies par l'utilisateur.

| Adresse | bas-gauche | haut-droite | Ce que le code en fait |
|---|---|---|---|
| `$019CF6` | 6 | 206 | `CLR.W`, `CMP.W`, `SUB.W`, passé en paramètre |
| `$018434` | 5 | −38 | `ADDQ.W #5` / `SUBQ.W #5` — déplacement par pas fixes |
| `$01AFB4` | −563 | 3529 | lu/écrit en `MOVE.L` — 32 bits |
| `$01AF1C` | 4 | 2 | écrit puis empilé en paramètre ; un `DIVS #5` le consomme |

**`$019CF6` est le meilleur candidat pour le X du palet** : 6 → 206 balaie la largeur
d'un espace 0-255, dans le bon sens pour un impact à gauche puis à droite.

⚠️ **Candidat, pas conclusion.** À confirmer en lisant les routines complètes qui les
manipulent, pas seulement l'instruction qui les référence.
