#!/usr/bin/env python3
"""Localise les banques sonores .ECH dans une image disque.

Format lu dans le chargeur a 0x014B64 (voir FINDINGS.md) :

    +$00  mot    N1   -> $1AFEC
    +$02  mot    N2   -> $1AFEA
    +$04  long[] table d'offsets, relatifs au debut du fichier

Le chargeur relocalise les N2 premiers offsets en une table de pointeurs
a $1AFEE, saute une entree, puis construit N1 enregistrements de 12 octets
a $1B06E :

    +$00  long  curseur   (initialise au debut)
    +$04  long  debut     = base + table[i+1]
    +$08  long  longueur  = table[i+2] - table[i+1]

La longueur etant une difference d'offsets consecutifs, la table est
croissante et son dernier element vaut la taille du fichier. C'est la
signature : deux petits compteurs suivis d'une suite strictement
croissante de mots longs plausibles.

    python tools/trouver_ech.py work/img/disk1.img work/assets/ech
"""
import sys, os, struct

MAX_ENTREES = 1000
MAX_FICHIER = 400000

def candidat(b, o):
    if o + 8 > len(b):
        return None
    n1, n2 = struct.unpack_from('>HH', b, o)
    if not (1 <= n1 <= MAX_ENTREES and 1 <= n2 <= MAX_ENTREES):
        return None
    total = n1 + n2 + 2
    fin_table = 4 + 4 * total
    if o + fin_table > len(b):
        return None
    t = list(struct.unpack_from('>%dL' % total, b, o + 4))
    # croissante, commence apres la table, reste dans une taille de fichier
    if t[0] < fin_table or t[-1] > MAX_FICHIER:
        return None
    if any(t[i] > t[i+1] for i in range(total - 1)):
        return None
    if len(set(t)) < total // 2:
        return None
    return n1, n2, t

def main(chemin, dest=None):
    b = open(chemin, 'rb').read()
    trouves = []
    o = 0
    while o < len(b) - 8:
        r = candidat(b, o)
        if r:
            n1, n2, t = r
            trouves.append((o, n1, n2, t))
            o += max(t[-1], 2)
        else:
            o += 2
    print(f"=== {os.path.basename(chemin)} : {len(trouves)} banque(s) .ECH ===")
    print()
    for o, n1, n2, t in trouves:
        longueurs = [t[i+1] - t[i] for i in range(len(t) - 1)]
        print(f"  offset ${o:06X} (secteur {o//512:>3})  N1={n1} N2={n2}  "
              f"taille={t[-1]} o")
        print(f"     {len(t)} offsets, longueurs {min(longueurs)}..{max(longueurs)}")
    if dest and trouves:
        os.makedirs(dest, exist_ok=True)
        base = os.path.splitext(os.path.basename(chemin))[0]
        for o, n1, n2, t in trouves:
            n = os.path.join(dest, f"{base}_{o:06x}.ech")
            open(n, 'wb').write(b[o:o+t[-1]])
        print()
        print(f"  ecrits dans {dest}")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
