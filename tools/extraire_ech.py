#!/usr/bin/env python3
"""Extrait les sons numerises d'une banque .ECH en fichiers WAV.

Le STF n'a pas de DMA audio. Le jeu joue quand meme du son numerise, en
modulant les volumes des TROIS voies du YM2149 : chaque octet de
l'echantillon indexe un triplet de volumes dans une table de 256 entrees
a 0x014296, et une interruption Timer A en consomme un par tic.

Cela a ete etabli, pas suppose :

  - la table fait EXACTEMENT 256 entrees de 8 octets (une par valeur
    d'octet possible), toutes de la forme (R8=v1, R9=v2, R10=v3) ;
  - en ajustant par moindres carres une courbe de DAC a 15 inconnues, le
    modele "amplitude proportionnelle a (127 - octet signe)" tombe a
    2,4 % d'erreur, contre 5,3 % pour la loi croissante et 17,8 % pour la
    valeur absolue ;
  - la courbe reconstituee a des rapports successifs autour de 1,4, soit
    3 dB par pas : la signature du YM2149.

Les echantillons sont donc du PCM signe 8 bits, stocke INVERSE.

Format de la banque, lu dans le chargeur a 0x014B64 :

    +$00  mot    N1  (nombre d'echantillons)
    +$02  mot    N2  (nombre de sequences)
    +$04  long[] table d'offsets, relatifs au debut du fichier

    table[1..N2]        -> les sequences, 4 octets chacune
    table[N2+1]         -> saute
    table[N2+2 ...]     -> les echantillons ; la longueur de chacun est la
                           difference avec l'offset suivant

Une sequence est une suite de paires (numero d'echantillon, TADR),
terminee par $FF. TADR est le diviseur du Timer A ; le prescaler vaut 4
(TACR = 1), et l'horloge du MFP 2 457 600 Hz, d'ou :

    frequence = 2457600 / (4 * TADR)

    python tools/extraire_ech.py work/assets/ech/disk1_019200.ech work/assets/wav
"""
import sys, os, struct

HORLOGE_MFP = 2457600
PRESCALER   = 4

def lire(b):
    n1, n2 = struct.unpack_from('>HH', b, 0)
    total = n1 + n2 + 3
    t = [struct.unpack_from('>L', b, 4*m)[0] for m in range(1, total)]
    tab = lambda m: t[m-1]
    sequences = []
    for i in range(n2):
        o = tab(i+1)
        paires, j = [], o
        while j + 1 < len(b) and b[j] != 0xFF:
            paires.append((b[j], b[j+1]))
            j += 2
        sequences.append(paires)
    echantillons = []
    for j in range(n1):
        i = n2 + 1 + j
        debut, fin = tab(i+1), tab(i+2)
        echantillons.append(b[debut:fin])
    return n1, n2, sequences, echantillons

def wav(chemin, donnees, frequence):
    """PCM 8 bits non signe. L'octet stocke est inverse : l'amplitude est
    proportionnelle a (127 - valeur signee), ce qui donne directement un
    octet non signe."""
    pcm = bytes((127 - (s - 256 if s > 127 else s)) & 0xFF for s in donnees)
    n = len(pcm)
    en_tete = (b'RIFF' + struct.pack('<L', 36 + n) + b'WAVEfmt '
               + struct.pack('<LHHLLHH', 16, 1, 1, frequence, frequence, 1, 8)
               + b'data' + struct.pack('<L', n))
    open(chemin, 'wb').write(en_tete + pcm)

def main(src, dest):
    b = open(src, 'rb').read()
    n1, n2, sequences, echantillons = lire(b)
    print(f"=== {os.path.basename(src)} : {n1} echantillon(s), {n2} sequence(s) ===")
    print()
    freq = {}
    for k, s in enumerate(sequences):
        print(f"  sequence {k} : " + ', '.join(
            f"echantillon {e} a TADR {t} = {HORLOGE_MFP//(PRESCALER*t)} Hz"
            for e, t in s if t))
        for e, t in s:
            if t:
                freq.setdefault(e, t)
    print()
    os.makedirs(dest, exist_ok=True)
    base = os.path.splitext(os.path.basename(src))[0]
    for k, d in enumerate(echantillons):
        t = freq.get(k)
        f = HORLOGE_MFP // (PRESCALER * t) if t else 10000
        n = os.path.join(dest, f"{base}_{k}.wav")
        wav(n, d, f)
        duree = len(d) / f
        note = '' if t else '  (frequence inconnue, 10000 Hz par defaut)'
        print(f"  echantillon {k} : {len(d):>6} octets, {f:>5} Hz, "
              f"{duree:5.2f} s -> {os.path.basename(n)}{note}")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
