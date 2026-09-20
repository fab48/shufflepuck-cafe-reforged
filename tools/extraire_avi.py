#!/usr/bin/env python3
"""Extrait les trames PNG d'un AVI produit par Hatari (--avi-vcodec png).

Un AVI est un conteneur RIFF : les trames video sont dans des morceaux
nommes '00dc'. Avec le codec PNG, chaque morceau EST un fichier PNG.
"""
import sys, os, struct

def trames(chemin):
    d = open(chemin,'rb').read()
    if d[:4] != b'RIFF': raise SystemExit("pas un fichier RIFF/AVI")
    i = 12
    n = 0
    while i + 8 <= len(d):
        idc = d[i:i+4]
        taille = struct.unpack_from('<I', d, i+4)[0]
        if idc in (b'LIST', b'RIFF'):
            i += 12; continue
        corps = d[i+8:i+8+taille]
        if idc.endswith(b'dc') and corps[:8] == b'\x89PNG\r\n\x1a\n':
            yield n, corps; n += 1
        i += 8 + taille + (taille & 1)

def main(avi, dossier, pas=1):
    os.makedirs(dossier, exist_ok=True)
    k = 0
    for n, png in trames(avi):
        if n % pas: continue
        open(os.path.join(dossier, f"trame_{n:05d}.png"), 'wb').write(png)
        k += 1
    print(f"{k} trames extraites dans {dossier}")

if __name__ == '__main__':
    pas = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    main(sys.argv[1], sys.argv[2], pas)
