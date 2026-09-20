#!/usr/bin/env python3
"""Inventaire des chaines du binaire, et qui les utilise.

Deux pieges evites ici :

  1. `4E 5D 4E 75 4E 55` se lit "N]NuNU" en ASCII : c'est `unlk a5 / rts /
     link a5`, pas une chaine. Un extracteur naif en sort des centaines.
     On ne retient donc que ce qui ressemble a du langage.
  2. Ce compilateur adresse ses litteraux en PC-RELATIF. Chercher
     l'adresse d'une chaine comme mot long dans le binaire ne donne RIEN.
     Il faut passer par le desassemblage et lire les operandes resolus.

Une chaine sans reference signale du code que la recursion n'a pas
atteint — c'est aussi un indicateur de couverture.

    python tools/chaines.py work/dump/loaded.ram
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))
from recursif import explorer, GRAINES
from carte import prologues

LO, HI = 0x008000, 0x01B700

def langage(s):
    """Du texte, pas du code lu de travers.

    Le critere qui separe proprement : un vrai mot contient une suite d'au
    moins trois minuscules, ou d'au moins quatre majuscules. `mzHx`,
    `TOBgHz` et `N]NuNU` echouent aux deux ; `sprites`, `INTBAR` et
    `Inserer le disque` passent. Les extensions de fichier (`.PC1`) sont
    admises a part, trop courtes pour ce test.
    """
    if len(s) < 4:
        return False
    if re.fullmatch(r"\.[A-Z0-9]{2,3}", s):
        return True
    return (any(len(m) >= 3 for m in re.findall(r"[a-z]+", s))
            or any(len(m) >= 4 for m in re.findall(r"[A-Z]+", s)))

def extraire(ram):
    out, a = {}, LO
    while a < HI:
        if 32 <= ram[a] < 127:
            d = a
            while d < HI and 32 <= ram[d] < 127:
                d += 1
            if d < HI and ram[d] == 0:
                s = ram[a:d].decode('latin1')
                if langage(s):
                    out[a] = s
            a = d + 1
        else:
            a += 1
    return out

def main(chemin):
    ram = open(chemin, 'rb').read()
    ch = extraire(ram)
    p, m = prologues(ram)
    vus, _, _ = explorer(ram, sorted(set(GRAINES) | set(p) | set(m)))

    refs = {}
    for pc, i in vus.items():
        for mo in re.finditer(r'\$([0-9a-f]+)', i.op_str):
            v = int(mo.group(1), 16)
            if v in ch:
                refs.setdefault(v, []).append(pc)

    print(f"=== {len(ch)} chaines ; {len(refs)} referencees par du code atteint ===\n")
    for a in sorted(ch):
        ou = refs.get(a)
        marque = ' '.join(f"{x:05x}" for x in sorted(ou)[:4]) if ou else '-- code non atteint --'
        print(f"  {a:05x}  {ch[a]!r:<54} {marque}")

if __name__ == '__main__':
    main(sys.argv[1])
