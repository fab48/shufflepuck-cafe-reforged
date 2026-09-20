#!/usr/bin/env python3
"""Lit un systeme de fichiers FAT12 Atari et en extrait les fichiers.

    python tools/fat12.py work/img/disk2.img            # liste
    python tools/fat12.py work/img/disk2.img work/assets/disk2   # extrait
"""
import struct, sys, os

def lire(img):
    u16 = lambda o: struct.unpack_from('<H', img, o)[0]
    ops   = u16(11)          # octets par secteur
    spc   = img[13]          # secteurs par cluster
    res   = u16(14)          # secteurs reserves
    nfat  = img[16]
    ndir  = u16(17)
    spf   = u16(22)
    deb_fat = res * ops
    deb_dir = (res + nfat * spf) * ops
    deb_dat = deb_dir + ndir * 32

    fat = img[deb_fat: deb_fat + spf * ops]
    def suivant(c):
        o = c + c // 2
        v = fat[o] | (fat[o+1] << 8)
        return (v >> 4) if (c & 1) else (v & 0x0FFF)

    fichiers = []
    for i in range(ndir):
        e = img[deb_dir + i*32: deb_dir + i*32 + 32]
        if e[0] in (0x00, 0xE5):
            continue
        attr = e[11]
        if attr & 0x08:          # nom de volume
            continue
        nom = e[0:8].decode('latin1').rstrip()
        ext = e[8:11].decode('latin1').rstrip()
        plein = f"{nom}.{ext}" if ext else nom
        # Le jeu de caracteres Atari n'est pas du cp1252 : on garde le nom
        # brut pour l'ecriture et une forme sure pour l'affichage.
        sur = ''.join(c if 32 <= ord(c) < 127 else f"<{ord(c):02X}>" for c in plein)
        debut = struct.unpack_from('<H', e, 26)[0]
        taille = struct.unpack_from('<I', e, 28)[0]
        date = struct.unpack_from('<H', e, 24)[0]
        heure = struct.unpack_from('<H', e, 22)[0]
        j, m, an = date & 31, (date >> 5) & 15, 1980 + (date >> 9)
        fichiers.append({
            'nom': plein, 'sur': sur, 'taille': taille, 'cluster': debut, 'attr': attr,
            'date': f"{j:02d}/{m:02d}/{an}",
            'heure': f"{(heure>>11):02d}:{(heure>>5)&63:02d}",
        })
    def contenu(f):
        out = bytearray(); c = f['cluster']
        while 2 <= c < 0xFF0:
            o = deb_dat + (c - 2) * spc * ops
            out += img[o: o + spc * ops]
            c = suivant(c)
        return bytes(out[:f['taille']])
    return fichiers, contenu

def main(chemin, dest=None):
    img = open(chemin, 'rb').read()
    fichiers, contenu = lire(img)
    print(f"=== {len(fichiers)} fichiers dans {os.path.basename(chemin)} ===\n")
    print(f"  {'nom':<16} {'taille':>8}   date        heure")
    total = 0
    for f in sorted(fichiers, key=lambda x: x['nom']):
        print(f"  {f['sur']:<16} {f['taille']:>8}   {f['date']}  {f['heure']}")
        total += f['taille']
    print(f"\n  total : {total} octets")
    if dest:
        os.makedirs(dest, exist_ok=True)
        for f in fichiers:
            d = contenu(f)
            open(os.path.join(dest, f['sur']), 'wb').write(d)
        print(f"  extraits dans {dest}")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
