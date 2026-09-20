#!/usr/bin/env python3
"""Cartographie exacte d'une image disque : ce qui est identifie, ce qui reste.

Aucune des deux disquettes n'a de systeme de fichiers exploitable (FAT
blanchie, repertoire vide). La seule facon de savoir ce qu'il y a dessus
est de reconnaitre chaque format par sa signature et de VERIFIER chaque
reconnaissance par une egalite de taille. Ce qui reste apres cela est ce
qu'on ne sait pas encore lire -- et c'est le chiffre qui compte.

    python tools/carte_disque.py work/img/disk1.img
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trouver_pc1, trouver_cpl, trouver_ech
from tc0 import decompresser

SECTEUR = 512

def reconnaitre(b):
    """Renvoie [(debut, fin, description)] pour tout ce qui est identifie."""
    md = trouver_pc1.Cs if False else None
    trouves = []
    from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
    cs = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
    for o in range(0, len(b) - 0x22, SECTEUR):
        # .PC1 : $8000, palette ST, decompression a exactement 32000 octets
        if b[o] == 0x80 and b[o+1] == 0x00 and trouver_pc1.palette_valide(b, o):
            r = trouver_pc1.depacker(b, o + 0x22, len(b))
            if r:
                trouves.append((o, o + r[1] - o, f"PC1  image 320x200"))
                continue
        # .CPL : deux mots, RLE inverse
        comp, brut = struct.unpack_from('>HH', b, o)
        if 8 <= comp <= len(b)-o-4 and 256 <= brut <= 65535 and comp <= brut:
            r = trouver_cpl.depacker(b, o+4, o+4+comp+2, brut)
            if r and abs(r[1] - comp) <= 1:
                trouves.append((o, o + 4 + comp, f"CPL  {brut} o decompresses"))
                continue
        # .TC0 : deux mots longs, codage par paires
        lc, lb = struct.unpack_from('>LL', b, o)
        if 16 <= lc < len(b)-o and lc < lb <= 4*lc + 4096:
            try:
                d, fin = decompresser(b, o+8, lb)
                if fin - o - 8 == lc:
                    n = struct.unpack_from('>H', d, 2)[0] // 4
                    trouves.append((o, o + 8 + lc, f"TC0  {lb} o, {n} partie(s)"))
                    continue
            except Exception:
                pass
        # .ECH : deux compteurs, table d'offsets croissante
        r = trouver_ech.candidat(b, o)
        if r:
            n1, n2, t = r
            trouves.append((o, o + t[-1], f"ECH  {n1} echantillon(s), {n2} sequence(s)"))
    return sorted(trouves)

def main(chemin):
    b = open(chemin, 'rb').read()
    tr = reconnaitre(b)
    couv = bytearray(len(b))
    print(f"=== {os.path.basename(chemin)} : {len(b)} octets, {len(b)//SECTEUR} secteurs ===")
    print()
    print(f"  {'secteurs':<14} {'octets':>8}  contenu")
    for a, e, n in tr:
        for k in range(a, min(e, len(b))):
            couv[k] = 1
        print(f"  {a//SECTEUR:>4}-{(e-1)//SECTEUR:<9} {e-a:>8}  {n}")
    reste = []
    a = 0
    while a < len(b):
        if couv[a]:
            a += 1; continue
        d = a
        while a < len(b) and not couv[a]:
            a += 1
        reste.append((d, a))
    print()
    print(f"  identifie      : {sum(couv)} octets ({100*sum(couv)//len(b)} %)")
    print(f"  non identifie  : {len(b)-sum(couv)} octets, {len(reste)} zone(s)")
    for d, f in reste:
        seg = b[d:f]
        z = seg.count(0)*100//len(seg)
        print(f"    {d//SECTEUR:>4}-{(f-1)//SECTEUR:<5} {f-d:>7} o   nuls {z:>3} %")

if __name__ == '__main__':
    main(sys.argv[1])
