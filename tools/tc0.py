#!/usr/bin/env python3
"""Decompresseur .TC0 : le format des neuf adversaires.

Le chargeur a 0x01542C lit deux mots longs (taille compressee, taille
decompressee), alloue la sortie, charge le compresse a la FIN de cette
meme allocation, decompresse en place, puis relocalise la table
d'offsets en tete -- la meme structure de banque de sprites que .CPL.

Le decompresseur est a 0x01554A. C'est un CODAGE PAR PAIRES D'OCTETS :
certaines valeurs d'octet sont des symboles qui se developpent en deux
autres octets, eux-memes developpables. Le fichier se decoupe en blocs :

    +$00  octet  N, nombre de paires (0 = bloc non compresse)
    +$01  octet  drapeau : non nul s'il reste des blocs
    +$02  mot    nombre d'octets du bloc, en PETIT-BOUTISTE
                 (le code lit l'octet de poids faible en premier)
    puis, si N != 0 : N symboles, N premiers octets, N seconds octets

L'expansion est recursive mais le 68000 n'a pas de recursion ici : elle
est deroulee sur la pile, avec deux zeros empiles comme marqueur de
fond. Quand plusieurs paires partagent un symbole, une liste chainee les
relie et le code retient la derniere dont l'index est INFERIEUR a
l'index courant -- c'est ce qui interdit les cycles.

Cette fonction est une transcription instruction par instruction, pas
une reconstruction d'apres l'idee generale : les etiquettes portent les
adresses d'origine.

    python tools/tc0.py fichier.tc0 sortie.bin
"""
import sys, struct


def decompresser(src, i=0, attendu=None):
    out = bytearray()
    while True:
        n = src[i]; drapeau = src[i+1]
        taille = src[i+2] | (src[i+3] << 8)      # petit-boutiste
        i += 4

        if n == 0:                                # L15674 : bloc brut
            out += src[i:i+taille]
            i += taille
        else:
            A = [0]*(n+1); B = [0]*(n+1); C = [0]*(n+1)
            for k in range(1, n+1): A[k] = src[i]; i += 1
            for k in range(1, n+1): B[k] = src[i]; i += 1
            for k in range(1, n+1): C[k] = src[i]; i += 1

            tete = [0]*256                        # L155DC : chainage par symbole
            suivant = [0]*(n+2)
            for d0 in range(1, n+1):
                d1 = A[d0]
                suivant[d0] = tete[d1]
                tete[d1] = d0

            for _ in range(taille):               # L155FC
                d1 = src[i]; i += 1               # L15610
                d0 = d1
                if tete[d0] == 0:
                    out.append(d0)
                    continue
                d0 = tete[d0]
                pile = [(0, 0)]
                etat = 'L15650'
                while True:
                    if etat == 'L15650':
                        d2 = C[d0]
                        pile.append((d0, d2))
                        d1 = B[d0]
                        etat = 'L1562C'
                    elif etat == 'L1562C':
                        d2 = d1
                        if tete[d2] == 0:
                            etat = 'L15668'
                        elif d0 > tete[d2]:       # bhi : cmp.b (a3,d2.w),d0
                            d0 = tete[d2]             # paire definie plus tot : valable
                            etat = 'L15650'
                        else:
                            limite = d0
                            d0 = tete[d2]
                            etat = 'L15640'
                    elif etat == 'L15640':
                        d0 = suivant[d0]
                        if d0 == 0:
                            d1 = d2
                            etat = 'L15668'
                        elif d0 < limite:
                            etat = 'L15650'
                        # sinon on reboucle sur L15640
                    elif etat == 'L15668':
                        out.append(d1)
                        d0, d2 = pile.pop()
                        if d0 == 0:
                            break
                        d1 = d2
                        etat = 'L1562C'
        if not drapeau:
            break
    if attendu is not None and len(out) != attendu:
        raise ValueError(f"{len(out)} octets produits, {attendu} attendus")
    return bytes(out), i


def fichier(chemin):
    b = open(chemin, 'rb').read()
    comp, brut = struct.unpack_from('>LL', b, 0)
    d, _ = decompresser(b, 8, brut)
    return d


if __name__ == '__main__':
    d = fichier(sys.argv[1])
    open(sys.argv[2], 'wb').write(d)
    print(f"  {len(d)} octets -> {sys.argv[2]}")
