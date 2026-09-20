#!/usr/bin/env python3
"""Extrait la voix de chaque adversaire depuis son fichier .TC0.

Un .TC0 porte deux parties. La partie 1 est la banque de sprites. La
partie 0 est une BANQUE SONORE, au format .ECH exactement : deux
compteurs, une table d'offsets, N2 sequences de paires (echantillon,
TADR) terminees par $FF, puis N1 echantillons.

Chaque adversaire a donc ses propres sons, et une sequence enchaine
souvent trois ou quatre echantillons pour composer une replique.

La conversion en WAV est celle de tools/extraire_ech.py : PCM signe
8 bits stocke inverse, frequence = 2457600 / (4 * TADR).

    python tools/extraire_voix.py work/assets/tc0 work/assets/voix
"""
import sys, os, struct, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extraire_ech import wav, HORLOGE_MFP, PRESCALER


def banque(d, base):
    """Lit une banque au format .ECH placee a `base` dans le tampon `d`.
    Les offsets y sont relatifs a `base`, pas au debut du fichier."""
    n1, n2 = struct.unpack_from('>HH', d, base)
    total = n1 + n2 + 3
    t = [struct.unpack_from('>L', d, base + 4*m)[0] for m in range(1, total)]
    tab = lambda m: t[m-1]
    sequences = []
    for i in range(n2):
        o = base + tab(i+1)
        paires, j = [], o
        while j + 1 < len(d) and d[j] != 0xFF:
            paires.append((d[j], d[j+1]))
            j += 2
        sequences.append(paires)
    echantillons = []
    for j in range(n1):
        i = n2 + 1 + j
        echantillons.append(d[base+tab(i+1) : base+tab(i+2)])
    return n1, n2, sequences, echantillons


def main(src, dest):
    os.makedirs(dest, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(src, '*.bin'))):
        d = open(f, 'rb').read()
        p0 = struct.unpack_from('>L', d, 0)[0]
        n1, n2, sequences, echantillons = banque(d, p0)
        base = os.path.splitext(os.path.basename(f))[0]
        print(f"=== {base} : {n1} echantillon(s), {n2} sequence(s) ===")
        freq = {}
        for k, s in enumerate(sequences):
            lisible = ' + '.join(f"#{e}@{HORLOGE_MFP//(PRESCALER*t)}Hz"
                                 for e, t in s if t)
            print(f"  sequence {k} : {lisible}")
            for e, t in s:
                if t:
                    freq.setdefault(e, t)
        for k, ech in enumerate(echantillons):
            if len(ech) < 64:
                continue
            t = freq.get(k)
            hz = HORLOGE_MFP // (PRESCALER * t) if t else 10000
            n = os.path.join(dest, f"{base}_{k}.wav")
            wav(n, ech, hz)
        print(f"  -> {sum(1 for e in echantillons if len(e) >= 64)} fichier(s) WAV")
        print()


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
