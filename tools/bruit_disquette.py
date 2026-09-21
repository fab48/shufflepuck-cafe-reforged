#!/usr/bin/env python3
"""Le bruit de disquette de l'accueil web -- PAS un son du jeu d'origine.

Source : « reading floppy disc 2 » (freesound_community, 35303), un
enregistrement de lecteur. On en garde le debut, coupe dans le creux
silencieux vers 3,1 s, avec un fondu de 60 ms pour eviter le clic.

    python -m pip install miniaudio
    python tools/bruit_disquette.py chemin/vers/le.mp3
"""
import sys, os, wave, miniaudio

TAUX, COUPE, FONDU = 22050, 3.15, 0.06
d = miniaudio.decode_file(sys.argv[1], output_format=miniaudio.SampleFormat.SIGNED16,
                          nchannels=1, sample_rate=TAUX)
n, f = int(COUPE * TAUX), int(FONDU * TAUX)
s = list(d.samples[:n + f])
for i in range(f):
    s[n + i] = int(s[n + i] * (1 - i / f))
sortie = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      'web', 'assets', 'bruit_disquette.wav')
with wave.open(sortie, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(TAUX)
    w.writeframes(b''.join(int(v).to_bytes(2, 'little', signed=True) for v in s))
print('%s : %.2f s' % (sortie, len(s) / TAUX))
