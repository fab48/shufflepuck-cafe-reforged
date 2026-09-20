#!/usr/bin/env python3
"""Exporte tous les assets extraits vers un format exploitable par un canvas.

Rien n'est redessine ni retouche ici : les images sortent telles qu'elles
sont sur les disquettes, a la palette pres, qui est convertie de $0RGB
(3 bits par composante) vers du RGB 8 bits. L'upscale et le recolorage
viendront apres, sur ces fichiers-la.

Produit dans web/assets/ :

    fond_<nom>.png       les ecrans 320x200, en RGB opaque
    sprites_<nom>.png    les banques, en planches RGBA (couleur 0 = transparent)
    sprites_<nom>.json   la position et la taille de chaque sprite
    son_<nom>.wav        les echantillons, a leur frequence d'origine
    manifeste.json       l'inventaire complet, avec les constantes du moteur

    python tools/exporter_web.py
"""
import os
import sys
import json
import glob
import struct

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, 'tools'))

from stgfx import decode_planar, st_palette, write_png, write_png_rgba, degas_vers_ecran
from trouver_pc1 import depacker as depack_pc1
from rendre_cpl import sprites as sprites_cpl
from extraire_voix import banque
from extraire_ech import wav, HORLOGE_MFP, PRESCALER
import tc0

TRAVAIL = os.path.join(RACINE, 'work')
SORTIE = os.path.join(RACINE, 'web', 'assets')

# Les noms viennent du manifeste de chargement lu a 0x00D190 et de l'ordre
# des .TC0 sur la disquette 2. Les correspondances marquees d'un ? ne sont
# pas etablies : je nomme par position, pas par identification.
ECRANS = {
    'disk1_011000': 'presents',
    'disk1_013200': 'titre',
    'disk1_03f200': 'terrain',
    'disk1_04f000': 'scores',
    'disk1_051400': 'champion',
}
BANQUES = {
    'disk1_042c00': 'bar',        # barsprit
    'disk1_04be00': 'interface',  # sprites
}


def planche(sp, colonnes=8, marge=1):
    """Range les sprites en grille et renvoie (pixels, rectangles)."""
    if not sp:
        return [], []
    lmax = max(w for w, _, _ in sp)
    hmax = max(h for _, h, _ in sp)
    n = (len(sp) + colonnes - 1) // colonnes
    W = colonnes * (lmax + marge) + marge
    H = n * (hmax + marge) + marge
    img = [[0] * W for _ in range(H)]
    rects = []
    for k, (w, h, px) in enumerate(sp):
        cx = marge + (k % colonnes) * (lmax + marge)
        cy = marge + (k // colonnes) * (hmax + marge)
        for y in range(h):
            for x in range(w):
                img[cy + y][cx + x] = px[y][x]
        rects.append({'x': cx, 'y': cy, 'w': w, 'h': h})
    return img, rects


def sprites_tc0(d):
    """La partie 1 d'un .TC0 : meme structure qu'un .CPL."""
    p1 = struct.unpack_from('>L', d, 4)[0]
    nb = struct.unpack_from('>L', d, p1)[0] // 4
    off = [struct.unpack_from('>L', d, p1 + 4 * k)[0] for k in range(nb)]
    out = []
    for o in off:
        a = p1 + o
        w, h = d[a], d[a + 1]
        lignes = []
        for y in range(h):
            ligne = []
            for mot in range(w):
                pl = [struct.unpack_from('>H', d, a + 2 + (y * w + mot) * 8 + i * 2)[0]
                      for i in range(4)]
                for bit in range(15, -1, -1):
                    ligne.append(sum(((pl[i] >> bit) & 1) << i for i in range(4)))
            lignes.append(ligne)
        out.append((w * 16, h, lignes))
    return out


def main():
    os.makedirs(SORTIE, exist_ok=True)
    manifeste = {'ecrans': {}, 'sprites': {}, 'sons': {}, 'adversaires': []}

    # --- les ecrans .PC1 -------------------------------------------------
    palettes = {}
    for f in sorted(glob.glob(os.path.join(TRAVAIL, 'assets', 'pc1', '*.pc1'))):
        cle = os.path.splitext(os.path.basename(f))[0]
        nom = ECRANS.get(cle)
        if nom is None:
            continue
        b = open(f, 'rb').read()
        mots = struct.unpack_from('>16H', b, 2)
        pal = st_palette(mots)
        palettes[nom] = pal
        brut, _ = depack_pc1(b, 0x22, len(b))
        lignes = decode_planar(degas_vers_ecran(brut), 320, 200)
        chemin = os.path.join(SORTIE, 'fond_%s.png' % nom)
        write_png(chemin, lignes, pal)
        manifeste['ecrans'][nom] = {
            'fichier': os.path.basename(chemin),
            'largeur': 320, 'hauteur': 200,
            'palette': ['#%02x%02x%02x' % c for c in pal],
        }
        print('  fond    %-12s %s' % (nom, os.path.basename(chemin)))

    # La palette de reference pour les sprites est celle du terrain : c'est
    # l'ecran sur lequel ils sont dessines.
    pal_jeu = palettes.get('terrain') or list(palettes.values())[0]

    # --- les banques .CPL ------------------------------------------------
    for f in sorted(glob.glob(os.path.join(TRAVAIL, 'assets', 'cpl', '*.bin'))):
        cle = os.path.splitext(os.path.basename(f))[0]
        nom = BANQUES.get(cle)
        if nom is None:
            continue
        sp = sprites_cpl(open(f, 'rb').read())
        img, rects = planche(sp)
        chemin = os.path.join(SORTIE, 'sprites_%s.png' % nom)
        w, h = write_png_rgba(chemin, img, pal_jeu)
        json.dump({'image': os.path.basename(chemin), 'largeur': w, 'hauteur': h,
                   'sprites': rects},
                  open(os.path.join(SORTIE, 'sprites_%s.json' % nom), 'w'), indent=1)
        manifeste['sprites'][nom] = {'fichier': 'sprites_%s.json' % nom,
                                     'nombre': len(rects)}
        print('  sprites %-12s %d sprites, %dx%d' % (nom, len(rects), w, h))

    # --- les neuf adversaires -------------------------------------------
    for k, f in enumerate(sorted(glob.glob(os.path.join(TRAVAIL, 'assets', 'tc0', '*.bin')))):
        d = open(f, 'rb').read()
        nom = 'adv%d' % k
        sp = sprites_tc0(d)
        img, rects = planche(sp, colonnes=6)
        chemin = os.path.join(SORTIE, 'sprites_%s.png' % nom)
        w, h = write_png_rgba(chemin, img, pal_jeu)
        json.dump({'image': os.path.basename(chemin), 'largeur': w, 'hauteur': h,
                   'sprites': rects},
                  open(os.path.join(SORTIE, 'sprites_%s.json' % nom), 'w'), indent=1)

        p0 = struct.unpack_from('>L', d, 0)[0]
        n1, n2, sequences, echantillons = banque(d, p0)
        sons = []
        for j, ech in enumerate(echantillons):
            if len(ech) < 64:
                continue
            hz = None
            for s in sequences:
                for e, t in s:
                    if e == j and t:
                        hz = HORLOGE_MFP // (PRESCALER * t)
                        break
                if hz:
                    break
            hz = hz or 10000
            nf = 'son_%s_%d.wav' % (nom, j)
            wav(os.path.join(SORTIE, nf), ech, hz)
            sons.append({'fichier': nf, 'frequence': hz})
        manifeste['adversaires'].append({
            'sprites': 'sprites_%s.json' % nom,
            'nombre_sprites': len(rects),
            'sons': sons,
            'sequences': [[{'echantillon': e, 'tadr': t,
                            'frequence': HORLOGE_MFP // (PRESCALER * t) if t else 0}
                           for e, t in s] for s in sequences],
        })
        print('  advers. %-12s %d sprites, %d son(s)' % (nom, len(rects), len(sons)))

    # --- les deux banques sonores ----------------------------------------
    for f in sorted(glob.glob(os.path.join(TRAVAIL, 'assets', 'ech', '*.ech'))):
        b = open(f, 'rb').read()
        n1, n2, sequences, echantillons = banque(b, 0)
        nom = 'musique' if len(b) > 100000 else 'bruitages'
        entrees = []
        for j, ech in enumerate(echantillons):
            if len(ech) < 64:
                continue
            hz = None
            for s in sequences:
                for e, t in s:
                    if e == j and t:
                        hz = HORLOGE_MFP // (PRESCALER * t)
                        break
                if hz:
                    break
            hz = hz or 10000
            nf = 'son_%s_%d.wav' % (nom, j)
            wav(os.path.join(SORTIE, nf), ech, hz)
            entrees.append({'fichier': nf, 'frequence': hz})
        manifeste['sons'][nom] = {
            'echantillons': entrees,
            'sequences': [[{'echantillon': e, 'tadr': t,
                            'frequence': HORLOGE_MFP // (PRESCALER * t) if t else 0}
                           for e, t in s] for s in sequences],
        }
        print('  son     %-12s %d echantillon(s), %d sequence(s)'
              % (nom, len(entrees), len(sequences)))

    # --- la table des neuf adversaires ----------------------------------
    # Lue dans le dump memoire, pas recopiee. L'ordre est celui de la table
    # $19D14 ; il ne correspond PAS forcement a l'ordre des .TC0 sur la
    # disquette, et cette correspondance n'est pas etablie.
    ram = open(os.path.join(TRAVAIL, 'dump', 'loaded.ram'), 'rb').read()
    B, PAS = 0x19D14, 0x56
    CHAMPS = [('largeur', 0x08), ('reflex_x', 0x0a), ('reflex_y', 0x0c),
              ('accel_x', 0x0e), ('accel_y', 0x10), ('reflex_x2', 0x12),
              ('reflex_y2', 0x14), ('accel_x2', 0x16), ('accel_y2', 0x18),
              ('x_min', 0x1e), ('x_max', 0x20), ('y_pres', 0x22), ('y_loin', 0x24),
              ('vr_droite', 0x26), ('v_attente_x', 0x28), ('v_attente_y', 0x2a),
              ('vr_pres', 0x2c), ('pas_gauche', 0x2e), ('v_attaque', 0x30),
              ('pas_arriere', 0x32), ('pas_avant', 0x34), ('v_defense', 0x36),
              ('pas_frappe_y', 0x38), ('disp_x_min', 0x3a), ('disp_x_max', 0x3c),
              ('disp_y_min', 0x3e), ('disp_y_max', 0x40), ('cible_x_min', 0x42),
              ('cible_x_max', 0x44), ('cible_y_min', 0x46), ('cible_y_max', 0x48),
              ('erreur_visee', 0x4a), ('seuil_reaction', 0x4e),
              ('pas_simulation', 0x50)]
    mot = lambda o: struct.unpack_from('>h', ram, o)[0]
    table = []
    for k in range(9):
        a = B + k * PAS
        ptr = struct.unpack_from('>L', ram, a + 0x52)[0]
        fin = ram.index(bytes(1), ptr)
        bloc = {'nom': ram[ptr:fin].decode('latin1')}
        for champ, off in CHAMPS:
            bloc[champ] = mot(a + off)
        table.append(bloc)
    manifeste['table_adversaires'] = table
    # le bloc court du joueur, 32 octets, juste avant la table
    joueur = {'y': mot(0x19CF4 + 0x02), 'largeur': mot(0x19CF4 + 0x08)}
    for champ, off in CHAMPS[1:9]:
        joueur[champ] = mot(0x19CF4 + off)
    manifeste['joueur'] = joueur
    print('  table   %-12s %d adversaires : %s'
          % ('parametres', len(table), ', '.join(b['nom'] for b in table)))

    # --- les constantes du moteur ---------------------------------------
    manifeste['moteur'] = {
        'mur_x': 226, 'mur_reflexion': 452,
        'y_joueur': 295, 'y_adversaire': 1205, 'y_fond': 1500,
        'palet_dx_max': 150, 'palet_dy_max': 300,
        'souris_max': 32, 'depl_max': 200, 'limite_mur': 250,
        'pourcent': 100,
        'proj_echelle': 411, 'proj_recul': 643, 'ecran_centre': 160,
        'proj_y': {'t_num': 207, 't_den': 970, 'sol': 193,
                   'hauteur_num': 164, 'hauteur_dec': 9},
        'son_rebond_base': 4, 'son_rebond_pas': 68,
    }
    json.dump(manifeste, open(os.path.join(SORTIE, 'manifeste.json'), 'w'), indent=1)
    print()
    print('  manifeste.json ecrit dans %s' % SORTIE)


if __name__ == '__main__':
    main()
