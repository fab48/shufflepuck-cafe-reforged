#!/usr/bin/env python3
"""Extrait les trames d'un AVI produit par Hatari (--avirecord).

Un AVI est un conteneur RIFF : les trames video sont dans des morceaux
nommes '00dc' ou '00db'. Selon le codec choisi, le morceau contient soit
un fichier PNG complet, soit une image BMP brute (DIB sans en-tete de
fichier). Les deux cas sont geres, et le BMP est converti en PNG a froid.

    python tools/extraire_avi.py partie.avi work/captures/trames [pas]
"""
import sys, os, struct, zlib

SIG_PNG = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])


def trames(chemin):
    """Rend (numero, donnees) pour chaque morceau video du conteneur."""
    d = open(chemin, 'rb').read()
    if d[:4] != b'RIFF':
        raise SystemExit("pas un fichier RIFF/AVI")
    i, n = 12, 0
    while i + 8 <= len(d):
        idc = d[i:i+4]
        taille = struct.unpack_from('<I', d, i+4)[0]
        if idc in (b'LIST', b'RIFF'):
            i += 12
            continue
        if idc.endswith(b'dc') or idc.endswith(b'db'):
            yield n, d[i+8:i+8+taille]
            n += 1
        i += 8 + taille + (taille & 1)


def morceau_png(typ, donnees):
    c = typ + donnees
    return (struct.pack('>I', len(donnees)) + c
            + struct.pack('>I', zlib.crc32(c) & 0xffffffff))


def png_depuis_rvb(largeur, hauteur, lignes):
    return (SIG_PNG
            + morceau_png(b'IHDR', struct.pack('>IIBBBBB', largeur, hauteur,
                                               8, 2, 0, 0, 0))
            + morceau_png(b'IDAT', zlib.compress(bytes(lignes), 6))
            + morceau_png(b'IEND', b''))


def bmp_vers_png(brut):
    """Convertit un DIB 24 bits (en-tete de 40 octets) en PNG."""
    if len(brut) < 40:
        return None
    larg = struct.unpack_from('<i', brut, 4)[0]
    haut = struct.unpack_from('<i', brut, 8)[0]
    bpp = struct.unpack_from('<H', brut, 14)[0]
    if bpp != 24 or larg <= 0 or haut <= 0:
        return None
    pas_ligne = (larg * 3 + 3) & ~3
    pix = brut[40:]
    if len(pix) < pas_ligne * haut:
        return None
    lignes = bytearray()
    for y in range(haut - 1, -1, -1):          # le BMP stocke de bas en haut
        o = y * pas_ligne
        lignes.append(0)                       # filtre PNG : aucun
        for x in range(larg):
            b = pix[o + x*3]
            g = pix[o + x*3 + 1]
            r = pix[o + x*3 + 2]
            lignes += bytes((r, g, b))
    return png_depuis_rvb(larg, haut, lignes)


def main(avi, dossier, pas=1):
    os.makedirs(dossier, exist_ok=True)
    ecrites = ignorees = 0
    for n, brut in trames(avi):
        if n % pas:
            continue
        donnees = brut if brut[:8] == SIG_PNG else bmp_vers_png(brut)
        if donnees is None:
            ignorees += 1
            continue
        open(os.path.join(dossier, "trame_%05d.png" % n), 'wb').write(donnees)
        ecrites += 1
    print("%d trames extraites dans %s" % (ecrites, dossier))
    if ignorees:
        print("%d morceaux non reconnus" % ignorees)


if __name__ == '__main__':
    p = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    main(sys.argv[1], sys.argv[2], p)
