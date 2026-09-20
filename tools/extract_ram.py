#!/usr/bin/env python3
"""Extrait la RAM ST d'un instantane Hatari (.sav).

Reperage : l'ST ecrit trois valeurs magiques en bas de memoire au demarrage.
On cherche leur alignement mutuel pour localiser l'offset 0 de la RAM, plutot
que de supposer une structure de fichier.
    $000420 memvalid  = $752019
    $00043A memval2   = $237698AA
    $00051A memval3   = $5555AAAA
"""
import sys, gzip, struct, os

MAGICS = [(0x420, 0x752019), (0x43A, 0x237698AA), (0x51A, 0x5555AAAA)]

def load(path):
    raw = open(path, 'rb').read()
    if raw[:2] == b'\x1f\x8b':
        print("  instantane compresse (gzip) -> decompression")
        raw = gzip.decompress(raw)
    return raw

def find_ram_base(b):
    """Cherche un offset X tel que les trois magies tombent a X+adresse."""
    needle = struct.pack('>I', MAGICS[0][1])
    hits = []
    start = 0
    while True:
        i = b.find(needle, start)
        if i < 0: break
        start = i + 1
        base = i - MAGICS[0][0]
        if base < 0: continue
        score = sum(1 for off, val in MAGICS
                    if base + off + 4 <= len(b)
                    and struct.unpack_from('>I', b, base + off)[0] == val)
        hits.append((score, base))
    hits.sort(reverse=True)
    return hits

def main(path, out, size=0x100000):
    b = load(path)
    print(f"  taille brute : {len(b)} octets")
    hits = find_ram_base(b)
    if not hits:
        print("  !! aucune signature ST trouvee. Structure inattendue.")
        print("  premiers octets :", b[:64].hex(' '))
        return 1
    print(f"  {len(hits)} candidat(s) ; meilleur score {hits[0][0]}/3")
    for score, base in hits[:4]:
        print(f"    offset {base} (0x{base:x}) score {score}/3")
    score, base = hits[0]
    if score < 2:
        print("  !! confiance insuffisante, on s'arrete")
        return 1
    ram = b[base:base+size]
    open(out, 'wb').write(ram)
    print(f"  ecrit : {out} ({len(ram)} octets)")
    # controles de coherence
    ssp, pc = struct.unpack_from('>II', ram, 0)
    print(f"  vecteur 0 : SSP=0x{ssp:08x}  PC=0x{pc:08x}")
    nz = sum(1 for c in ram if c)
    print(f"  remplissage : {100*nz//len(ram)}% d'octets non nuls")
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
