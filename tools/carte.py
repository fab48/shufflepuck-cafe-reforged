#!/usr/bin/env python3
"""Carte honnete de l'image memoire : code, donnees, vide.

Le chiffre de couverture n'a de sens que si le denominateur est juste.
Trois erreurs corrigees ici :

  1. Le code ne commence pas a 0x008D3E. Cette zone est vide dans les
     cinq instantanes ; c'etait un tampon, pas du programme.
  2. Un desassemblage recursif peut decoder deux fois les memes octets
     quand une graine tombe au milieu d'une instruction. On compte donc
     les octets DISTINCTS, pas la somme des tailles.
  3. Les chaines, les tables de registres YM et les tables d'index ne
     sont pas du code et n'ont pas a figurer au denominateur.

    python tools/carte.py work/dump/loaded.ram
"""
import sys, os, glob
sys.path.insert(0, os.path.dirname(__file__))
from recursif import explorer, GRAINES

LO, HI = 0x008000, 0x018400

def prologues(ram):
    """Ce compilateur ouvre chaque fonction par `link a5,#-N`. Un `4E 55`
    precede d'un `rts` ou d'un `unlk` est une fonction, pas un hasard."""
    p = [a for a in range(LO, HI-4, 2)
         if ram[a] == 0x4e and ram[a+1] == 0x55
         and int.from_bytes(ram[a-2:a], 'big') in (0x4e75, 0x4e5d)]
    m = [a for a in range(LO, HI-4, 2)
         if ram[a] == 0x48 and ram[a+1] == 0xe7
         and int.from_bytes(ram[a-2:a], 'big') in (0x4e75, 0x4e73, 0x4e5d)]
    return p, m

def zone_chargee(dossier):
    """Un octet nul dans TOUS les instantanes n'a jamais rien contenu."""
    dumps = [open(f, 'rb').read() for f in glob.glob(os.path.join(dossier, '*.ram'))]
    charge = bytearray(HI - LO)
    for d in dumps:
        for a in range(LO, HI):
            if d[a]:
                charge[a-LO] = 1
    return charge, len(dumps)

def main(chemin):
    ram = open(chemin, 'rb').read()
    p, m = prologues(ram)
    graines = sorted(set(GRAINES) | set(p) | set(m))
    vus, fonctions, appels = explorer(ram, graines)

    charge, n_dumps = zone_chargee(os.path.dirname(chemin))
    # n'attribuer au code que ce qui est effectivement charge : une graine
    # qui part dans un tampon vide produit des instructions fantomes.
    code = bytearray(HI - LO)
    double = 0
    for pc, i in vus.items():
        for k in range(pc, pc + i.size):
            if not charge[k-LO]:
                continue
            if code[k-LO]:
                double += 1
            code[k-LO] = 1

    n_charge = sum(charge)
    n_code = sum(code)
    print(f"  graines            : {len(GRAINES)} connues, {len(p)} link a5, {len(m)} movem")
    print(f"  instantanes croises: {n_dumps}")
    print()
    print(f"  plage              : 0x{LO:06x}-0x{HI:06x}   {HI-LO} octets")
    print(f"  jamais rien contenu: {HI-LO-n_charge} octets  (tampons, BSS)")
    print(f"  reellement charge  : {n_charge} octets")
    print(f"  code atteint       : {n_code} octets  ->  {100*n_code//n_charge} % du charge")
    print(f"  decode deux fois   : {double} octets (graines suspectes)")
    print(f"  fonctions          : {len(fonctions)}")

    trous = []
    a = 0
    while a < HI - LO:
        if code[a] or not charge[a]:
            a += 1; continue
        d = a
        while d < HI - LO and not code[d] and charge[d]:
            d += 1
        if d - a >= 32:
            trous.append((a+LO, d+LO))
        a = d
    print(f"\n  zones chargees mais non atteintes (>=32 o) : {len(trous)}"
          f"   total {sum(b-a for a, b in trous)} octets")
    for a, b in sorted(trous, key=lambda z: z[0]-z[1])[:20]:
        seg = ram[a:b]
        asc = sum(1 for x in seg if 32 <= x < 127) * 100 // len(seg)
        note = 'texte' if asc > 80 else ('donnees ?' if asc > 25 else '')
        print(f"    0x{a:06x}-0x{b:06x} {b-a:>6} o   ascii {asc:>3} %  {note}")
    return vus, fonctions, appels

if __name__ == '__main__':
    main(sys.argv[1])
