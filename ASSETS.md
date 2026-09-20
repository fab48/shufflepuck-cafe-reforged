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
