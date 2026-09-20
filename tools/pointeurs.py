#!/usr/bin/env python3
"""Recolte des tables de pointeurs de fonctions.

La recursion suit jsr/bsr/bra/bcc. Elle ne peut pas suivre `jsr (a0)`
quand a0 vient d'une table. Ces tables sont pourtant partout dans un
programme compile : machines a etats, listes de handlers, menus.

Signature recherchee : une suite de mots longs alignes dont la valeur
tombe dans la plage de code, est paire, et pointe sur une instruction
que capstone sait decoder. Un faux positif isole est probable ; une
suite de trois est deja improbable par hasard.

    python tools/pointeurs.py work/dump/loaded.ram
"""
import sys, collections
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000

CODE_LO, CODE_HI = 0x008000, 0x018400
SCAN_LO, SCAN_HI = 0x008000, 0x01B700
MIN_SUITE = 3

# Une instruction qui ouvre une fonction compilee : link, movem de
# sauvegarde, ou un test/move ordinaire. Ce qui suit disqualifie.
INVRAISEMBLABLE = {
    'illegal', 'reset', 'stop', 'rtr', 'trapv',
}

def plausible(md, ram, adr):
    """L'adresse decode-t-elle en une instruction credible ?"""
    if not (CODE_LO <= adr < CODE_HI) or adr & 1:
        return False
    liste = list(md.disasm(ram[adr:adr+10], adr, 1))
    if not liste:
        return False
    return liste[0].mnemonic not in INVRAISEMBLABLE

def main(chemin):
    ram = open(chemin, 'rb').read()
    md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)

    # 1. marquer chaque mot long aligne qui ressemble a un pointeur
    est_ptr = {}
    for a in range(SCAN_LO, SCAN_HI - 4, 2):
        v = int.from_bytes(ram[a:a+4], 'big')
        if plausible(md, ram, v):
            est_ptr[a] = v

    # 2. regrouper en suites de pas 4
    tables, a = [], SCAN_LO
    vus = set()
    for a in sorted(est_ptr):
        if a in vus:
            continue
        suite, c = [], a
        while c in est_ptr:
            suite.append(est_ptr[c]); vus.add(c); c += 4
        if len(suite) >= MIN_SUITE:
            tables.append((a, suite))

    cibles = set()
    print("=== tables de pointeurs candidates ===\n")
    for a, suite in tables:
        cibles.update(suite)
        apercu = ' '.join(f"{v:06x}" for v in suite[:8])
        suffixe = ' ...' if len(suite) > 8 else ''
        print(f"  0x{a:06x}  {len(suite):>3} entrees : {apercu}{suffixe}")
    print(f"\n  tables    : {len(tables)}")
    print(f"  cibles    : {len(cibles)} adresses distinctes")
    print("\nGRAINES_PTR = [")
    for i, c in enumerate(sorted(cibles)):
        fin = '\n' if i % 6 == 5 else ' '
        print(f"    0x{c:06x},", end=fin)
    print("\n]")
    return cibles

if __name__ == '__main__':
    main(sys.argv[1])
