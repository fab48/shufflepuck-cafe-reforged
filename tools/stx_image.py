#!/usr/bin/env python3
"""Reconstruit une image disque brute depuis un conteneur Pasti (.STX).

Une tentative anterieure avait echoue parce qu'elle bricolait les secteurs
residant dans l'image de piste. Ici on s'en tient au cas simple et on le
VERIFIE : la disquette 2 de Shufflepuck n'a aucune protection (83 pistes,
9 secteurs partout, zero octet flou), donc chaque secteur a son descripteur
et ses donnees propres. Le lecteur refuse de deviner : tout secteur absent
laisse un trou explicite, et le compte des trous est affiche.

Disposition d'un enregistrement de piste :

    +$00 long  taille de l'enregistrement
    +$04 long  taille du masque flou
    +$08 mot   nombre de secteurs
    +$0A mot   drapeaux (bit 0 : descripteurs presents)
    +$0C mot   taille MFM de la piste
    +$0E octet numero de piste (bit 7 = face)
    +$0F octet type

    puis : descripteurs (16 o chacun), masque flou, zone de donnees.

Un descripteur :

    +$00 long  offset des donnees dans la zone
    +$04 mot   position en bits
    +$06 mot   duree de lecture
    +$08 six octets  champ d'identification : piste, face, secteur, taille
    +$0E octet statut FDC

    python tools/stx_image.py work/disks/disk2.stx sortie.img
"""
import struct, sys

def lire(chemin):
    b = open(chemin, 'rb').read()
    if b[:4] != b'RSY\0':
        raise SystemExit("ce n'est pas un conteneur Pasti")
    u16 = lambda o: struct.unpack_from('<H', b, o)[0]
    u32 = lambda o: struct.unpack_from('<I', b, o)[0]

    secteurs = {}            # (piste, face, secteur) -> donnees
    off = 16
    for _ in range(b[10]):
        taille, flou = u32(off), u32(off+4)
        nsec, drap = u16(off+8), u16(off+10)
        tnum = b[off+14]
        piste, face = tnum & 0x7f, tnum >> 7
        p = off + 16
        descs = []
        if drap & 0x01:
            for _ in range(nsec):
                descs.append((u32(p), b[p+10], b[p+11], b[p+14]))
                p += 16
        p += flou
        zone = p
        for dof, sec, tsz, statut in descs:
            n = 128 << tsz
            secteurs[(piste, face, sec)] = b[zone+dof: zone+dof+n]
        off += taille
    return secteurs

def image(secteurs, faces, spt=9, pistes=80):
    img = bytearray()
    trous = []
    for piste in range(pistes):
        for face in range(faces):
            for sec in range(1, spt+1):
                d = secteurs.get((piste, face, sec))
                if d is None or len(d) != 512:
                    trous.append((piste, face, sec))
                    d = bytes(512)
                img += d
    return bytes(img), trous

def main(src, dst):
    s = lire(src)
    faces = 1 + max(f for _, f, _ in s)
    img, trous = image(s, faces)
    print(f"  secteurs lus   : {len(s)}")
    print(f"  faces          : {faces}")
    print(f"  image          : {len(img)} octets")
    print(f"  secteurs manquants : {len(trous)}"
          + (f"  {trous[:6]}" if trous else ""))
    # verification : le BPB doit etre coherent
    o = struct.unpack_from('<H', img, 11)[0]
    spc, res, nfat, ndir, nsec = img[13], struct.unpack_from('<H', img, 14)[0], \
        img[16], struct.unpack_from('<H', img, 17)[0], struct.unpack_from('<H', img, 19)[0]
    spf = struct.unpack_from('<H', img, 22)[0]
    print(f"\n  BPB : {o} o/secteur, {spc} secteur(s)/cluster, {res} reserve(s),")
    print(f"        {nfat} FAT de {spf} secteurs, {ndir} entrees de repertoire, {nsec} secteurs")
    if o != 512:
        print("  !! BPB incoherent : l'image n'est pas bonne")
    open(dst, 'wb').write(img)
    print(f"\n  ecrit : {dst}")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
