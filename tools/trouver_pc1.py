#!/usr/bin/env python3
"""Localise les images Degas Elite compressees (.PC1) dans une image disque.

Aucune des deux disquettes n'a de systeme de fichiers : la FAT est blanchie
et le repertoire ne contient aucun nom. Le jeu lit donc par secteur absolu.
On ne peut pas demander la liste des fichiers ; on peut en revanche
reconnaitre leur forme.

Un .PC1 commence par :

    +$00  mot    $8000  (basse resolution, compresse)
    +$02  16 mots palette, format ST $0RGB : les nibbles de poids fort sont
          nuls et chaque composante tient sur 3 bits -> w & $F888 == 0
    +$22  donnees PackBits

Deux garde-fous contre les faux positifs :
  - les 16 mots doivent TOUS satisfaire la contrainte de palette ;
  - la decompression PackBits doit rendre exactement 32000 octets.

Le second est decisif : une suite d'octets quelconque ne se decompresse
pratiquement jamais sur la taille exacte d'un ecran ST.

    python tools/trouver_pc1.py work/img/disk2.img work/assets/pc1
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stgfx import decode_planar, st_palette, write_png, degas_vers_ecran

ECRAN = 32000          # 320x200x4 plans / 8

def palette_valide(b, o):
    for i in range(16):
        w = struct.unpack_from('>H', b, o + 2 + 2*i)[0]
        if w & 0xF888:
            return False
    return True

def depacker(b, o, limite):
    """PackBits, comme Degas Elite : n>=0 -> n+1 litteraux, n<0 -> 1-n
    repetitions. On s'arrete des qu'on a un ecran, ou qu'on sort du cadre."""
    out = bytearray()
    i = o
    while len(out) < ECRAN:
        if i >= limite:
            return None
        n = b[i]; i += 1
        if n < 128:
            k = n + 1
            if i + k > limite:
                return None
            out += b[i:i+k]; i += k
        elif n > 128:
            k = 257 - n
            if i >= limite:
                return None
            out += bytes([b[i]]) * k; i += 1
        else:
            return None            # $80 n'est pas utilise par Degas
    return (bytes(out), i) if len(out) == ECRAN else None

def main(chemin, dest=None):
    b = open(chemin, 'rb').read()
    trouves = []
    for o in range(0, len(b) - 0x22, 2):
        if b[o] != 0x80 or b[o+1] != 0x00:
            continue
        if not palette_valide(b, o):
            continue
        r = depacker(b, o + 0x22, len(b))
        if r is None:
            continue
        donnees, fin = r
        trouves.append((o, fin - o, donnees, b[o+2:o+0x22]))

    print(f"=== {os.path.basename(chemin)} : {len(trouves)} image(s) .PC1 ===\n")
    for o, taille, _, pal in trouves:
        mots = struct.unpack('>16H', pal)
        print(f"  offset ${o:06X}  (secteur {o//512:>3})  {taille:>6} octets compresses")
        print(f"     palette : " + ' '.join(f"{w:03x}" for w in mots))
    if dest and trouves:
        os.makedirs(dest, exist_ok=True)
        base = os.path.splitext(os.path.basename(chemin))[0]
        for o, taille, donnees, pal in trouves:
            n = os.path.join(dest, f"{base}_{o:06x}")
            open(n + '.pc1', 'wb').write(b[o:o+taille])
            couleurs = st_palette(struct.unpack('>16H', pal))
            lignes = decode_planar(degas_vers_ecran(donnees), 320, 200)
            write_png(n + '.png', lignes, couleurs)
        print()
        print(f"  ecrits dans {dest} : .pc1 d'origine et .png rendu")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
