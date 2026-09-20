#!/usr/bin/env python3
"""Decodage des graphismes Atari ST basse resolution.
   320x200, 4 plans de bits entrelaces par mots de 16 bits, 16 couleurs."""
import struct

def decode_planar(data, width_px, height, planes=4):
    """Renvoie une liste de lignes d'indices de couleur."""
    words_per_row = (width_px // 16) * planes
    out = []
    for y in range(height):
        row = []
        base = y * words_per_row * 2
        for chunk in range(width_px // 16):
            o = base + chunk * planes * 2
            if o + planes*2 > len(data): return out
            pl = [struct.unpack_from('>H', data, o + p*2)[0] for p in range(planes)]
            for bit in range(15, -1, -1):
                c = 0
                for p in range(planes):
                    c |= ((pl[p] >> bit) & 1) << p
                row.append(c)
        out.append(row)
    return out

def st_palette(words, ste=False):
    """Convertit 16 mots $0RGB en RGB 8 bits."""
    pal = []
    for w in words:
        if ste:
            r = ((w >> 8) & 7) << 1 | ((w >> 11) & 1)
            g = ((w >> 4) & 7) << 1 | ((w >> 7) & 1)
            b = (w & 7) << 1 | ((w >> 3) & 1)
            pal.append((r*17, g*17, b*17))
        else:
            r, g, b = (w >> 8) & 7, (w >> 4) & 7, w & 7
            pal.append((r*36, g*36, b*36))
    return pal

def write_png(path, rows, pal):
    import zlib
    h = len(rows); w = len(rows[0]) if h else 0
    raw = bytearray()
    for r in rows:
        raw.append(0)
        for c in r:
            raw += bytes(pal[c & 15])
    def chunk(t, d):
        c = t + d
        return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    png += chunk(b'IEND', b'')
    open(path, 'wb').write(png)
    return w, h


def degas_vers_ecran(brut, largeur=320, hauteur=200, plans=4):
    """Convertit la sortie PackBits d'un Degas .PC1 en memoire ecran ST.

    Piege verifie a l'image : Degas range chaque ligne PLAN PAR PLAN
    (40 octets du plan 0, puis 40 du plan 1, ...), alors que l'ecran ST
    ENTRELACE les plans par mots de 16 bits. Rendre la sortie PackBits
    telle quelle donne du bruit qui ressemble a une image cassee -- il
    faut reentrelacer.
    """
    mots = largeur // 16
    par_plan = mots * 2
    par_ligne = par_plan * plans
    ecran = bytearray(hauteur * par_ligne)
    for y in range(hauteur):
        ligne = brut[y*par_ligne:(y+1)*par_ligne]
        for p in range(plans):
            plan = ligne[p*par_plan:(p+1)*par_plan]
            for w in range(mots):
                o = y*par_ligne + w*plans*2 + p*2
                ecran[o:o+2] = plan[w*2:w*2+2]
    return bytes(ecran)


def write_png_rgba(path, rows, pal, transparent=0):
    """Ecrit un PNG RGBA. L'index `transparent` devient entierement
    transparent : sur ST, la couleur 0 sert de fond aux sprites."""
    import zlib
    h = len(rows); w = len(rows[0]) if h else 0
    opaque = bytes([255])
    vide = bytes([0])
    raw = bytearray()
    for r in rows:
        raw.append(0)
        for c in r:
            i = c & 15
            raw += bytes(pal[i]) + (vide if i == transparent else opaque)
    def chunk(t, d):
        c = t + d
        return (struct.pack('>I', len(d)) + c
                + struct.pack('>I', zlib.crc32(c) & 0xffffffff))
    png = bytes([137, 80, 78, 71, 13, 10, 26, 10])
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    png += chunk(b'IEND', b'')
    open(path, 'wb').write(png)
    return w, h
