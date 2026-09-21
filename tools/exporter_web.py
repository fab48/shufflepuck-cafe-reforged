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
    # L'ordre est celui de l'index d'adversaire ($1B5AC), et le fichier est
    # celui que 0x00D786 charge pour cet index. Chaque .TC0 a ete identifie
    # en comparant les hauteurs de ses sprites a la table de placement que
    # 0x00D786 associe au meme index (8 correspondances completes sur 9 ;
    # bejin 6/18, seul fichier restant).
    ram = open(os.path.join(TRAVAIL, 'dump', 'loaded.ram'), 'rb').read()
    for vieux in glob.glob(os.path.join(SORTIE, '*adv[0-9]*')):
        os.remove(vieux)
    PERSOS = [  # (fichier charge, .TC0 sur la disquette 2, table de placement)
        ('skip', 'disk2_011c00', 0x188A8), ('visine', 'disk2_014600', 0x18A42),
        ('vinnie', 'disk2_019000', 0x18CA8), ('lexan', 'disk2_022a00', 0x18FC2),
        # La table de saut de 0x00D786 envoie l'index 4 sur « general » et
        # l'index 5 sur « nerual » -- pas dans l'ordre du listing.
        ('general', 'disk2_02ae00', 0x1926E), ('nerual', 'disk2_03d600', 0x19514),
        ('bejin', 'disk2_048600', 0x19708), ('biff', 'disk2_050c00', 0x198C4),
        ('droid', 'disk2_008200', 0x199FC),
    ]
    # Les scripts d'animation que 0x00F522 lance en debut de partie, par
    # index : (adresse, mode). Mode 1 = fond en boucle, 0 = une fois derriere.
    SCRIPTS = [
        [(0x18812, 1)], [(0x188F8, 1)],
        [(0x18AB4, 1), (0x18A82, 1), (0x18AC8, 0)],
        [(0x18D38, 1), (0x18D4C, 1), (0x18DB0, 0)],
        [(0x190C0, 1), (0x1908E, 1)], [], [(0x1958C, 1)], [], [(0x1990C, 1)],
    ]
    REACTIONS = [0x18894, 0x18A2E, 0x18C94, 0x18FAE, 0x1925A,
                 0x19500, 0x196F4, 0x198B0, 0x199E8]
    for k, (nom, disque, table) in enumerate(PERSOS):
        f = os.path.join(TRAVAIL, 'assets', 'tc0', disque + '.bin')
        d = open(f, 'rb').read()
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
        mot = lambda o: struct.unpack_from('>h', ram, o)[0]
        manifeste['adversaires'].append({
            'fichier': nom, 'tc0': disque,
            'placement': [[mot(table + 8 * i + j) for j in (0, 2, 4, 6)]
                          for i in range(len(rects))],
            'scripts': [{'adresse': a, 'mode': mode} for a, mode in SCRIPTS[k]],
            # $00F998 : les cinq reactions a un point, lancees en mode 0.
            'reactions': [struct.unpack_from('>L', ram, REACTIONS[k] + 4 * n)[0]
                          for n in range(5)],
            'sprites': 'sprites_%s.json' % nom,
            'nombre_sprites': len(rects),
            'sons': sons,
            'sequences': [[{'echantillon': e, 'tadr': t,
                            'frequence': HORLOGE_MFP // (PRESCALER * t) if t else 0}
                           for e, t in s] for s in sequences],
        })
        print('  advers. %-12s %d sprites, %d son(s)' % (nom, len(rects), len(sons)))

    # La zone memoire des scripts d'animation, telle quelle. Les scripts se
    # REECRIVENT : les fonctions de rappel du personnage modifient le numero
    # de sprite ou la duree d'une image directement dans ces octets. On les
    # exporte donc comme une memoire, pas comme une liste figee.
    import base64
    # $18400 : on inclut la scene du bar (placement $18444, scripts $18574 et
    # $1879A), qui precede les donnees des personnages.
    DEBUT, FIN = 0x18400, 0x19D00
    manifeste['memoire_scripts'] = {
        'debut': DEBUT,
        'octets': base64.b64encode(ram[DEBUT:FIN]).decode('ascii'),
    }

    # Les fonctions de rappel qui ne font que jouer des sons. Elles suivent
    # deux formes, reconnues ici au desassembleur plutot que recopiees :
    #   - une suite de « move.w #$80,-(a7) / move.w #$Xnn,-(a7) / jsr $112C0 »
    #     qui joue chaque son ;
    #   - la meme chose precedee de « jsr $FD94 / divs.w #$3 » : un seul des
    #     trois sons, tire au hasard.
    # $Xnn : X = banque (1 = bruitages, 2 = voix de l'adversaire), nn = sequence.
    from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
    md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
    def scripts_de(a):
        vus = set()
        while a not in vus and DEBUT <= a < FIN:
            vus.add(a)
            yield a
            if struct.unpack_from('>h', ram, a)[0] <= -3:
                return
            a += 10
    rappels = set()
    # Deux scripts lances par le moteur plutot qu'en debut de partie : le
    # service de Bejin ($195BE) et la pose de Dc3 ($199B6).
    autres = [0x195BE, 0x199B6, 0x18574, 0x1879A]   # + la boucle du bar et la bestiole
    for adv in manifeste['adversaires'] + [{'scripts': [{'adresse': a} for a in autres], 'reactions': []}]:
        for s in [x['adresse'] for x in adv['scripts']] + [x for x in adv['reactions'] if x]:
            for im in scripts_de(s):
                f = struct.unpack_from('>L', ram, im + 4)[0]
                if f:
                    rappels.add(f)
    sons_rappels, ignores = {}, []
    for f in sorted(rappels):
        ins = []
        for i in md.disasm(ram[f:f + 200], f):
            ins.append(i)
            if i.mnemonic == 'rts':
                break
        texte = [f"{i.mnemonic} {i.op_str}" for i in ins]
        ids = []
        for n in range(len(ins) - 1):
            if ins[n + 1].mnemonic == 'jsr' and '$112c0' in ins[n + 1].op_str \
                    and ins[n].mnemonic == 'move.w' and ins[n].op_str.startswith('#$'):
                ids.append(int(ins[n].op_str[2:].split(',')[0], 16))
        autre = [t for t in texte if not any(t.startswith(p) for p in (
            'link', 'unlk', 'rts', 'move.w #$80', 'move.w #$', 'jsr $112c0', 'addq.w #$4, a7',
            'moveq #$0, d0', 'jsr $fd94', 'ext.l', 'divs.w #$3', 'swap', 'bra', 'tst.l',
            'beq', 'subq.l #$1'))]
        if ids and not autre:
            sons_rappels[f] = {'hasard': any('divs.w #$3' in t for t in texte), 'sons': ids}
        else:
            ignores.append(f)
    manifeste['rappels_sons'] = {str(f): v for f, v in sons_rappels.items()}

    # La scene du bar (0x01205A) : l'ecran de choix de l'adversaire.
    #   zones $1A040 : x1, y1, x2, y2, valeur (index d'adversaire ; -1 sortie,
    #   -2 la bestiole, 9 l'enseigne), terminees par un x1 nul ;
    #   placement $18444 : x, y du BAS, largeur, hauteur -- en absolu ;
    #   champion : la chaine a $1A520, que rend $137D0.
    zones, a = [], 0x1A040
    while struct.unpack_from('>h', ram, a)[0]:
        zones.append([struct.unpack_from('>h', ram, a + 2 * i)[0] for i in range(5)])
        a += 10
    fin_nom = ram.index(bytes(1), 0x1A520)
    manifeste['bar'] = {
        'zones': zones,
        'placement': 0x18444,
        'boucle': 0x18574, 'bestiole': 0x1879A,
        'champion': ram[0x1A520:fin_nom].decode('latin1'),
        'musique': 2,                       # $11422 : banque 0, sequence 2
    }
    print('  rappels  %d fonctions de son reconnues ; non reconnues : %s'
          % (len(sons_rappels), ' '.join('%X' % f for f in ignores)))

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
              ('erreur_visee', 0x4a), ('tremblement', 0x4c), ('seuil_reaction', 0x4e),
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
    # $1A01A : le pointeur de bloc de chaque index d'adversaire, lu par
    # 0x0106DC. Il n'est PAS dans l'ordre : il echange les blocs 1<->2 et
    # 4<->5. Lexan (3) et Dc3 (8) pointent sur des copies de travail
    # ($1B5B6, $1B60C), faites de leur bloc.
    index_blocs = []
    for i in range(9):
        p = struct.unpack_from('>L', ram, 0x1A01A + 4 * i)[0]
        index_blocs.append({0x1B5B6: 3, 0x1B60C: 8}.get(p, (p - B) // PAS))
    manifeste['index_blocs'] = index_blocs

    # La fonte « quete.fnt ». Absente des disquettes sous forme de fichier
    # reconnaissable, mais chargee en memoire au demarrage : $1B53A pointe
    # dessus. Format lu dans $14F4E et $14FA4 :
    #   +0 premier caractere, +1 dernier, +2 hauteur, +3 octets par ligne
    #   +4 long : offset de la table des caracteres (un mot par caractere :
    #      12 bits de position en pixels dans la planche, 4 bits de largeur)
    #   +8 la planche, 1 bit par pixel, poids fort a gauche
    # Avance : largeur (3 si nulle) + l'espacement $1A710.
    f = struct.unpack_from('>L', ram, 0x1B53A)[0]
    prem, dern, haut, lb = ram[f], ram[f + 1], ram[f + 2], ram[f + 3]
    t = f + struct.unpack_from('>L', ram, f + 4)[0] - 2 * prem
    glyphes = {}
    for c in range(prem, dern + 1):
        d = struct.unpack_from('>H', ram, t + 2 * c)[0]
        x, w = d & 0xFFF, d >> 12
        lignes = []
        for y in range(haut):
            ligne = ram[f + 8 + y * lb: f + 8 + (y + 1) * lb]
            bits = ''.join('%08d' % int(bin(o)[2:]) for o in ligne)
            lignes.append(bits[x:x + w])
        glyphes[chr(c)] = {'l': w, 'p': lignes}
    manifeste['fonte'] = {'hauteur': haut,
                          'espacement': struct.unpack_from('>h', ram, 0x1A710)[0],
                          'glyphes': glyphes}
    print('  fonte    %d caracteres, hauteur %d' % (len(glyphes), haut))
    print('  index    -> blocs : %s' % index_blocs)
    # le bloc court du joueur, 32 octets, juste avant la table
    joueur = {'y': mot(0x19CF4 + 0x02), 'largeur': mot(0x19CF4 + 0x08)}
    for champ, off in CHAMPS[1:9]:
        joueur[champ] = mot(0x19CF4 + off)
    manifeste['joueur'] = joueur

    # La vitre : un cadre de fissure et 13 eclats, traces en lignes par
    # 0x00F164. Enregistrements de 14 octets a $19B04 (le cadre) et $19B12
    # (les eclats) : +0 pointeur vers des paires d'indices de sommets
    # terminees par un second indice nul, +4 vitesse X, +6 vitesse Y
    # initiale. Les sommets sont a $19BC8, deux mots chacun.
    def paires(p):
        out = []
        while ram[p + 1] != 0:
            out.append([ram[p], ram[p + 1]])
            p += 2
        return out
    enr = []
    for k in range(14):
        a = 0x19B04 + 14 * k
        enr.append({'lignes': paires(struct.unpack_from('>L', ram, a)[0]),
                    'vx': mot(a + 4), 'vy0': mot(a + 6)})
    n = 1 + max(max(i, j) for e in enr for i, j in e['lignes'])
    manifeste['vitre'] = {
        'cadre': enr[0]['lignes'],
        'eclats': enr[1:],
        'sommets': [[mot(0x19BC8 + 4 * i), mot(0x19BC8 + 4 * i + 2)] for i in range(n)],
    }
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
