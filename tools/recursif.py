#!/usr/bin/env python3
"""Desassemblage recursif : ne visite que ce qui s'execute reellement.

Le balayage lineaire traverse les donnees et fabrique des instructions
fantomes. Ici on part de points d'entree connus et on suit les branchements,
ce qui separe rigoureusement le code des donnees.

    python tools/recursif.py work/dump/loaded.ram
"""
import sys, re, struct, collections
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000

LO, HI = 0x008000, 0x018400

# Points d'entree etablis au fil du projet (voir PHYSICS.md).
GRAINES = [
    0x010466, 0x00feb0, 0x00feec, 0x00fe9e, 0x00fdec, 0x00fdce,
    0x00fb7a, 0x00db9c, 0x00dbc2, 0x010802, 0x01096c, 0x010a02,
    0x010ab6, 0x010bce, 0x010c7c, 0x010d44, 0x010eaa, 0x0110ba,
    0x00f23a, 0x00f28c, 0x0112c0, 0x011486, 0x0114e4, 0x011586,
    0x0115de, 0x014eec, 0x014eda, 0x017602, 0x01609e, 0x01034c,
    0x01023c, 0x00bdf8,
    # Gestionnaires d'interruption : installes dans la table des vecteurs,
    # jamais appeles par une instruction. Invisibles a la recursion, donc
    # indispensables comme graines.
    0x00886c,   # timer C du MFP, installe par 0x00BE16 -- horloge du jeu
    0x0087b4,   # file VBL, installee par 0x00BE08
    0x014240,   # vecteur $134, installe par 0x0141A4
    0x015914,   # timer C, installe par 0x015804

    # Cibles des 16 tables de saut du compilateur, decodees par
    # tools/tables_saut.py. Les deplacements y sont SIGNES et la borne
    # vient du cmp qui precede le jmp.
    0x00b9ec, 0x00b9fc, 0x00ba10, 0x00ba18, 0x00ba4a, 0x00ba64,
    0x00ba9a, 0x00d7de, 0x00d7fc, 0x00d81a, 0x00d838, 0x00d856,
    0x00d874, 0x00d896, 0x00d8b2, 0x00d8ce, 0x00e28e, 0x00e296,
    0x00e31a, 0x00e3b6, 0x00e56c, 0x00e6f0, 0x00e864, 0x00e88e,
    0x00ed64, 0x00ed68, 0x00ed88, 0x00ee64, 0x00ee68, 0x00ee88,
    0x00f0d8, 0x00f0dc, 0x00f0fc, 0x00f532, 0x00f546, 0x00f55a,
    0x00f58c, 0x00f5bc, 0x00f5be, 0x00f5e0, 0x00f5f2, 0x00f5f4,
    0x00f9ac, 0x00f9c2, 0x00f9d8, 0x00f9ee, 0x00fa04, 0x00fa18,
    0x00fa2c, 0x00fa40, 0x00fa54, 0x01035c, 0x010368, 0x0103d6,
    0x010466, 0x01054a, 0x010ed2, 0x010ee4, 0x010ef6, 0x010f06,
    0x010f18, 0x010f2a, 0x010f5c, 0x010f68, 0x011000, 0x0122bc,
    0x0122c4, 0x0122d2, 0x0122ea, 0x01238a, 0x012392, 0x0123d2,
    0x0123e0, 0x0123ee, 0x01244e, 0x012452, 0x01245c, 0x012472,
    0x012488, 0x01249c, 0x01252a, 0x012532, 0x012574, 0x01259c,
    0x012600, 0x01263a, 0x012648, 0x012a20, 0x012a28, 0x012a36,
    0x012a3c, 0x012a62, 0x012a68,
]

FIN_BLOC = {'rts', 'rte', 'rtr', 'jmp', 'bra.b', 'bra.w', 'bra.s', 'bra'}

def explorer(ram, graines):
    md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
    vus = {}                      # adresse -> instruction
    fonctions = set(graines)
    appels = collections.defaultdict(set)
    a_faire = list(graines)
    while a_faire:
        pc = a_faire.pop()
        while LO <= pc < HI and pc not in vus:
            paquet = ram[pc:pc+10]
            liste = list(md.disasm(paquet, pc, 1))
            if not liste:
                break
            i = liste[0]
            vus[pc] = i
            mn, ops = i.mnemonic, i.op_str

            cibles = []
            for m in re.finditer(r'\$([0-9a-f]+)', ops):
                v = int(m.group(1), 16)
                if LO <= v < HI:
                    cibles.append(v)

            if mn in ('jsr', 'bsr') or mn.startswith('bsr'):
                for c in cibles:
                    fonctions.add(c); appels[c].add(pc)
                    if c not in vus: a_faire.append(c)
            elif mn.startswith('b') and mn not in ('bsr', 'btst', 'bset', 'bclr', 'bchg'):
                for c in cibles:
                    if c not in vus: a_faire.append(c)
            elif mn.startswith('db'):
                for c in cibles:
                    if c not in vus: a_faire.append(c)

            if mn in FIN_BLOC or mn.startswith(('rts', 'rte', 'jmp', 'bra')):
                break
            pc += i.size
    return vus, fonctions, appels

def main(chemin):
    ram = open(chemin, 'rb').read()
    vus, fonctions, appels = explorer(ram, GRAINES)
    octets = sum(i.size for i in vus.values())
    print("=== desassemblage recursif ===\n")
    print(f"  graines            : {len(GRAINES)}")
    print(f"  instructions visitees : {len(vus)}")
    print(f"  octets de code atteints : {octets}")
    print(f"  fonctions decouvertes : {len(fonctions)}")
    # zones jamais atteintes
    trous = []
    a = LO
    while a < HI:
        if a in vus:
            a += vus[a].size; continue
        d = a
        while d < HI and d not in vus:
            d += 2
        if d - a >= 64: trous.append((a, d))
        a = d
    print(f"\n  zones jamais atteintes (>= 64 octets) : {len(trous)}")
    print(f"  total non atteint : {sum(b-a for a,b in trous)} octets")
    for a, b in sorted(trous, key=lambda z: z[0]-z[1])[:12]:
        print(f"    0x{a:06x} - 0x{b:06x}   {b-a:>6} o")
    return vus, fonctions, appels

if __name__ == '__main__':
    main(sys.argv[1])
