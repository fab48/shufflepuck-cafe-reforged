#!/usr/bin/env python3
"""L'editeur de parametres laisse dans le binaire par les developpeurs.

Loriciel a livre le jeu avec son outil de reglage encore dedans : une
table de widgets a 0x01A118, chacun portant un libelle EN FRANCAIS, un
pointeur vers la variable reglee, et ses bornes. Ce n'est pas une
hypothese sur la structure des raquettes : c'est la nomenclature des
auteurs.

Format d'un enregistrement, 26 octets :

    +$00  long   pointeur vers le libelle
    +$04  long   0
    +$08  long   variable liee (le "max" quand ce widget est un "min"), ou 0
    +$0C  long   ADRESSE DE LA VARIABLE REGLEE
    +$10  word   minimum (signe)
    +$12  word   maximum (signe)
    +$14  6 o    0

Le code de l'editeur n'est jamais atteint par la recursion : il est mort
dans la version commerciale. Ses donnees, elles, sont intactes.

    python tools/editeur.py work/dump/loaded.ram
"""
import sys

TABLE, PAS, FIN = 0x01A118, 0x1A, 0x01A40A

# Bases etablies par recoupement (voir FINDINGS.md).
BLOCS = [
    (0x19CF4, 0x20, "raquette du JOUEUR (statique)"),
    (0x1B60C, 0x56, "raquette de l'ADVERSAIRE (copie vivante)"),
]

def main(chemin):
    ram = open(chemin, 'rb').read()
    L = lambda a: int.from_bytes(ram[a:a+4], 'big')
    def W(a):
        v = int.from_bytes(ram[a:a+2], 'big')
        return v - 0x10000 if v >= 0x8000 else v
    def S(a):
        d = a
        while ram[d]:
            d += 1
        return ram[a:d].decode('latin1')

    def situer(adr):
        for base, taille, nom in BLOCS:
            if base <= adr < base + taille:
                return f"{nom}  +${adr-base:02X}"
        return f"variable globale $%05X" % adr

    print("=== editeur de parametres : table 0x01A118 ===\n")
    print(f"  {'libelle':<30} {'variable':<10} {'min':>6} {'max':>6}   emplacement")
    a = TABLE
    while a < FIN:
        lib, lie, var = L(a), L(a+8), L(a+0x0C)
        mn, mx = W(a+0x10), W(a+0x12)
        note = situer(var)
        if lie:
            note += f"   (borne haute : ${lie:05X})"
        print(f"  {S(lib):<30} ${var:05X}    {mn:>6} {mx:>6}   {note}")
        a += PAS

if __name__ == '__main__':
    main(sys.argv[1])
