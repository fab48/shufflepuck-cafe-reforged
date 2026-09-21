#!/usr/bin/env python3
"""Listing d'une plage, a partir du desassemblage recursif (code seulement).

    python tools/lister.py work/dump/loaded.ram 0x11900 0x13d00 > sortie.txt

Les trous (donnees) sont signales ; les fonctions appelees sont marquees.
"""
import sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
import recursif

ram = open(sys.argv[1], 'rb').read()
lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
vus, fonctions, appels = recursif.explorer(ram, recursif.GRAINES + [int(a, 16) for a in sys.argv[4:]])
a = lo
while a < hi:
    if a in vus:
        i = vus[a]
        if a in fonctions:
            print('\n; ---- %06x <- %s' % (a, ' '.join('%06x' % c for c in sorted(appels[a]))))
        print('%06x  %-10s %s' % (a, i.mnemonic, i.op_str))
        a += i.size
    else:
        d = a
        while d < hi and d not in vus:
            d += 2
        print('%06x  ; donnees %d o : %s' % (a, d - a, ram[a:min(d, a + 48)].hex()))
        a = d
