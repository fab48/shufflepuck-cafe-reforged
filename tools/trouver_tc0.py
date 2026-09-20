#!/usr/bin/env python3
"""Localise les fichiers .TC0 : les neuf adversaires.

Le chargeur a 0x01542C recoit un nom DYNAMIQUE -- celui choisi par la
table de saut a 0x00D7DE, qui egrene skip, visine, vinnie, lexan,
nerual, general, bejin, biff, droid. Les .TC0 sont donc les fichiers des
personnages, et la disquette 2, dont 91 % etait inexplique, en est
pleine.

En-tete : deux mots longs, taille compressee puis taille decompressee.
La validation est la meme que pour les autres formats et elle est
stricte : la decompression doit rendre EXACTEMENT la taille annoncee en
consommant EXACTEMENT la taille compressee annoncee.

    python tools/trouver_tc0.py work/img/disk2.img work/assets/tc0
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tc0 import decompresser

def main(chemin, dest=None):
    b = open(chemin, 'rb').read()
    # Les fichiers sont ecrits par secteur : inutile de sonder les offsets
    # intermediaires, et un balayage non aligne se perd apres la premiere
    # trouvaille.
    trouves = []
    for o in range(0, len(b) - 8, 512):
        comp, brut = struct.unpack_from('>LL', b, o)
        if not (16 <= comp < len(b) - o and comp < brut <= 4*comp + 4096):
            continue
        try:
            d, fin = decompresser(b, o + 8, brut)
        except Exception:
            continue
        if fin - o - 8 == comp:
            trouves.append((o, comp, brut, d))
    print(f"=== {os.path.basename(chemin)} : {len(trouves)} fichier(s) .TC0 ===")
    print()
    for o, comp, brut, d in trouves:
        n = struct.unpack_from('>H', d, 2)[0] // 4
        print(f"  offset ${o:06X} (secteur {o//512:>3})  {comp:>6} -> {brut:>6} o  "
              f"({100 - 100*comp//brut:>2} % de gain)  {n} partie(s)")
    if dest and trouves:
        os.makedirs(dest, exist_ok=True)
        base = os.path.splitext(os.path.basename(chemin))[0]
        for o, comp, brut, d in trouves:
            open(os.path.join(dest, f"{base}_{o:06x}.tc0"), 'wb').write(b[o:o+8+comp])
            open(os.path.join(dest, f"{base}_{o:06x}.bin"), 'wb').write(d)
        print()
        print(f"  ecrits dans {dest} : .tc0 d'origine et .bin decompresse")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
