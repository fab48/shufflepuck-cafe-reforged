#!/usr/bin/env python3
"""Localise et decompresse les fichiers .CPL (les sprites).

Le manifeste de chargement a 0x00D212 et 0x00D224 charge deux fichiers
.CPL : `barsprit` et `sprites`. Ce sont les personnages animes.

Le decompresseur est a 0x015116. Son en-tete :

    +$00  mot   taille compressee
    +$02  mot   taille decompressee (passee telle quelle au malloc)

puis un flux a octet de controle, dont la convention est l'INVERSE de
PackBits :

    c <  $80 : repeter c fois l'octet suivant     (consomme 2)
    c >= $80 : copier (c & $7F) octets litteraux  (consomme 1 + n)

Pas de "+1" sur les compteurs, contrairement a Degas. Un compteur nul
existe donc et ne produit rien.

Le critere de validation est double et strict : la decompression doit
rendre EXACTEMENT la taille annoncee en consommant EXACTEMENT la taille
compressee annoncee. Deux egalites simultanees sur des valeurs lues dans
le fichier : le hasard ne passe pas.

    python tools/trouver_cpl.py work/img/disk1.img work/assets/cpl
"""
import sys, os, struct

def depacker(b, o, fin, attendu):
    out = bytearray()
    i = o
    while i < fin and len(out) < attendu:
        c = b[i]; i += 1
        if c < 0x80:
            if i >= fin:
                return None
            out += bytes([b[i]]) * c
            i += 1
        else:
            n = c & 0x7F
            if i + n > fin:
                return None
            out += b[i:i+n]
            i += n
    if len(out) != attendu:
        return None
    return bytes(out), i - o

def main(chemin, dest=None):
    b = open(chemin, 'rb').read()
    trouves = []
    o = 0
    while o < len(b) - 8:
        comp, brut = struct.unpack_from('>HH', b, o)
        if not (8 <= comp <= len(b) - o - 4 and 256 <= brut <= 65535 and comp <= brut):
            o += 2
            continue
        r = depacker(b, o + 4, o + 4 + comp + 2, brut)
        if r and abs(r[1] - comp) <= 1:
            trouves.append((o, comp, brut, r[0]))
            o += comp
        else:
            o += 2
    print(f"=== {os.path.basename(chemin)} : {len(trouves)} fichier(s) .CPL ===")
    print()
    for o, comp, brut, _ in trouves:
        print(f"  offset ${o:06X} (secteur {o//512:>3})  "
              f"{comp:>6} o compresses -> {brut:>6} o  "
              f"({100 - 100*comp//brut:>2} % de gain)")
    if dest and trouves:
        os.makedirs(dest, exist_ok=True)
        base = os.path.splitext(os.path.basename(chemin))[0]
        for o, comp, brut, d in trouves:
            open(os.path.join(dest, f"{base}_{o:06x}.cpl"), 'wb').write(b[o:o+4+comp])
            open(os.path.join(dest, f"{base}_{o:06x}.bin"), 'wb').write(d)
        print()
        print(f"  ecrits dans {dest} : .cpl d'origine et .bin decompresse")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
