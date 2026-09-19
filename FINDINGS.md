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
