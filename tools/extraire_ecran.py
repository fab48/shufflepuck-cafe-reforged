#!/usr/bin/env python3
"""Extrait l'ecran d'un instantane Hatari (.sav) ou d'un dump RAM vers un PNG."""
import sys, gzip, struct, os
sys.path.insert(0, os.path.dirname(__file__))
from stgfx import decode_planar, st_palette, write_png

BASE_SAV = 0x000F95          # decalage RAM dans un .sav (voir FINDINGS.md)
PAL, SCR = 0x01B53E, 0x01B700

def charger(p):
    b = open(p,'rb').read()
    if b[:2] == b'\x1f\x8b':
        b = gzip.decompress(b)[BASE_SAV:BASE_SAV+0x100000]
    return b

def main(src, dst):
    ram = charger(src)
    ws  = [struct.unpack_from('>H', ram, PAL+i*2)[0] for i in range(16)]
    pal = st_palette(ws)
    rows = decode_planar(ram[SCR:SCR+32000], 320, 200)
    w,h = write_png(dst, rows, pal)
    print(f"{dst}  {w}x{h}")
    print("palette :", ' '.join('%03x'%x for x in ws))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
