# Configuration Hatari

## Choix et pourquoi

| Option | Valeur | Raison |
|---|---|---|
| `--machine st` | STF | le jeu est de 1989, antérieur au STE |
| `--tos tos162fr.img` | TOS 1.62 FR | TOS 2.06 casse beaucoup de titres de cette époque |
| `--compatible on` | 68000 précis | mode plus lent mais fidèle, utile sur disque protégé |
| `--fastfdc off` | — | **critique** : l'accélération FDC casse les protections |
| `--timer-d off` | — | le patch Timer-D double la vitesse mais fausse le timing |
| `--fast-boot off` | — | même raison, on ne patche rien |
| `--blitter off` | — | le STF n'en avait pas |
| `--memsize 1` | 1 Mo | configuration la plus courante à l'époque |
| `--zoom 2` | 640×400 | doublement entier de 320×200, sans interpolation |

## Si ça résiste

- TOS 1.62 est à l'origine un TOS de STE. Si Hatari renâcle ou si le jeu
  se comporte mal, essayer `--tos tos206fr.img`, ou se procurer un TOS 1.04.
- `--drive-a-heads 1` pour émuler un lecteur simple face, comme les disquettes
  (le BPB confirme 1 tête). Un lecteur double face lit normalement du simple
  face, mais une protection peut interroger la géométrie.
- Si le jeu réclame la disquette 2 sans la voir, la retirer du lecteur B et
  faire l'échange à la main dans le menu Hatari (F12).

## Upscale

`--zoom 2` donne un doublement propre sans filtrage. Pour aller plus loin en 4K,
superposer **Magpie** (open source, Windows) sur la fenêtre Hatari : il applique
FSR, Anime4K ou xBRZ en temps réel. Hatari 1.8 n'a pas de shaders.

## Vérifié au lancement (test réel)

Le jeu **démarre et atteint son écran-titre** : protection franchie, aucune erreur FDC.
Journal Hatari :
```
IPF : capsimage library version release=5 revision=1
STX : STX_Insert_internal drive=0 file=C:\SHUFFL~1\SHUFFL~2.STX size=836880
STX : STX_Insert_internal drive=1 file=C:\SHUFFL~1\SHUFFL~1.STX size=880818
```

### Correction : le TOS choisi force le mode STE
```
TOS versions 1.06 and 1.62 are for Atari STE only.
 ==> Switching to STE mode now.
```
`--machine st` est **ignoré** avec `tos162fr.img`. La machine émulée est donc une STE,
pas une STF. Le jeu fonctionne quand même. Pour une STF authentique il faudrait un
TOS 1.02 / 1.04, absent de `D:\hatari\TOS\`.

### Échange de disquettes
Le jeu réclame la disquette 2 **dans le lecteur A** ; la placer en B ne suffit pas.
Faire l'échange à chaud : `F12` → *Floppy disks* → *Drive A:* → *Browse* → disquette 2.

Le chargement est lent car `--fastfdc off` reproduit la vitesse réelle d'un lecteur
de disquette. C'est volontaire : l'accélération FDC casse les protections. Compter
plusieurs dizaines de secondes jusqu'à l'écran-titre.

## À propos de « Fast floppy access »

J'avais écrit ici que l'option était active malgré `--fastfdc off`, et que ma
recommandation était donc erronée. **C'était une mauvaise lecture de la capture
d'écran.** Le fichier `~/.hatari/hatari.cfg` indique `FastFloppy = FALSE`, en
accord avec le lanceur. L'accélération FDC est bien désactivée, comme voulu.

Leçon pour ce projet : ne pas tirer de conclusion d'une case à cocher lue sur une
image compressée. Vérifier dans le fichier de configuration.

## Confirmé à l'écran

Ligne de copyright du jeu : `Copyright 1989 Broderbund Software, Inc. — V1.0`.
Il s'agit donc de la **version 1.0**.

Les deux lecteurs sont déclarés *Double Sided* alors que les disquettes sont simple
face (BPB : 1 tête). Sans effet — un lecteur double face lit du simple face.

## Images de travail

`work/disks/disk1.stx` et `disk2.stx` : copies sous noms explicites, pour en finir
avec l'inversion des noms courts 8.3 (`SHUFFL~2` = disquette 1, `SHUFFL~1` = disquette 2)
qui est un piège à erreurs. Les originaux restent intacts dans le dossier d'archive.
Le dossier `work/` n'est pas versionné.

## Ne jamais précharger la disquette 2 dans le lecteur B

Hatari refuse d'insérer la même image dans deux lecteurs :
`cannot insert in the same drive`. En préchargeant `disk2.stx` en B, l'échange
vers le lecteur A échoue — il faut d'abord éjecter B.

Le lanceur ne charge donc plus que le lecteur A. L'échange en cours de partie se
fait sans obstacle : `F12` → *Floppy disks* → *Drive A:* → *Browse* → `disk2.stx`.
