#!/usr/bin/env python3
"""Rend une banque de sprites .CPL decompressee en planche PNG.

Structure, etablie et verifiee sur 57/57 sprites :

    +$00  long[]  table d'offsets ; le premier offset donne la taille de
                  la table, donc le nombre de sprites
    puis, a chaque offset :
    +$00  octet   largeur en mots de 16 pixels
    +$01  octet   hauteur en lignes
    +$02  ...     largeur * hauteur * 4 plans * 2 octets

Le test : la taille deduite de l'en-tete doit egaler la difference entre
deux offsets consecutifs. Trois autres conventions (en-tete de 4 ou 6
octets, plan de masque supplementaire) donnent 0/57 ; celle-ci donne
57/57.

La palette vient du fichier `jeu` -- l'ecran de terrain, charge en meme
temps que les sprites par la sequence 0x00D200.

    python tools/rendre_cpl.py banque.bin terrain.pc1 sortie.png
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stgfx import st_palette, write_png

def sprites(d):
    n = struct.unpack_from('>L', d, 0)[0] // 4
    off = [struct.unpack_from('>L', d, 4*k)[0] for k in range(n)]
    out = []
    for o in off:
        w, h = d[o], d[o+1]
        lignes = []
        p = o + 2
        for y in range(h):
            ligne = []
            for mot in range(w):
                plans = [struct.unpack_from('>H', d, p + (y*w + mot)*8 + i*2)[0]
                         for i in range(4)]
                for bit in range(15, -1, -1):
                    ligne.append(sum(((plans[i] >> bit) & 1) << i for i in range(4)))
            lignes.append(ligne)
        out.append((w*16, h, lignes))
    return out

def palette_pc1(chemin):
    b = open(chemin, 'rb').read()
    return st_palette(struct.unpack_from('>16H', b, 2))

def planche(sp, colonnes=8, marge=4):
    largeur = max(w for w, _, _ in sp)
    hauteur = max(h for _, h, _ in sp)
    lignes_n = (len(sp) + colonnes - 1) // colonnes
    W = colonnes * (largeur + marge) + marge
    H = lignes_n * (hauteur + marge) + marge
    img = [[0]*W for _ in range(H)]
    for k, (w, h, px) in enumerate(sp):
        cx = marge + (k % colonnes) * (largeur + marge)
        cy = marge + (k // colonnes) * (hauteur + marge)
        for y in range(h):
            for x in range(w):
                img[cy+y][cx+x] = px[y][x]
    return img

def main(banque, terrain, sortie):
    d = open(banque, 'rb').read()
    sp = sprites(d)
    pal = palette_pc1(terrain)
    print(f"  {len(sp)} sprites")
    for k, (w, h, _) in enumerate(sp):
        print(f"    {k:>2} : {w:>3} x {h:<3}", end='\n' if k % 5 == 4 else '   ')
    print()
    write_png(sortie, planche(sp), pal)
    print(f"  planche ecrite : {sortie}")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
