#!/usr/bin/env python3
"""Genere la table C des neuf adversaires depuis un dump memoire du jeu.

Aucune valeur n'est recopiee a la main : elles sont lues dans la table
$19D14 (pas de 86 octets), et l'identite de chaque bloc vient du pointeur
de nom en +$52 — les quatre derniers octets du bloc de 86.

    python tools/gen_table.py work/dump/loaded.ram
"""
import struct, sys

B, ST = 0x19D14, 0x56
CHAMPS = [('largeur',0x08),('reflex_x',0x0a),('reflex_y',0x0c),('accel_x',0x0e),('accel_y',0x10),
          ('reflex_x2',0x12),('reflex_y2',0x14),('accel_x2',0x16),('accel_y2',0x18),
          ('x_min',0x1e),('x_max',0x20),('y_pres',0x22),('y_loin',0x24),
          ('vr_droite',0x26),('v_attente_x',0x28),('v_attente_y',0x2a),('vr_pres',0x2c),
          ('pas_gauche',0x2e),('v_attaque',0x30),('pas_arriere',0x32),('pas_avant',0x34),
          ('v_defense',0x36),('pas_frappe_y',0x38),
          ('disp_x_min',0x3a),('disp_x_max',0x3c),('disp_y_min',0x3e),('disp_y_max',0x40),
          ('cible_x_min',0x42),('cible_x_max',0x44),('cible_y_min',0x46),('cible_y_max',0x48),
          ('erreur_visee',0x4a),('seuil_reaction',0x4e),('pas_simulation',0x50)]

def main(chemin):
    ram = open(chemin,'rb').read()
    s = lambda o: struct.unpack_from('>h', ram, o)[0]
    for k in range(9):
        a = B + k*ST
        nom = ram[0x010000 + s(a+0x54):][:12].split(b'\x00')[0].decode('latin1')
        print(f"  {{ /* {k} — {nom} */")
        print(f'    .nom = "{nom}",')
        ligne = '   '
        for champ, off in CHAMPS:
            bout = f' .{champ} = {s(a+off)},'
            if len(ligne) + len(bout) > 76:
                print(ligne); ligne = '   '
            ligne += bout
        print(ligne)
        print("  },")

if __name__ == '__main__':
    main(sys.argv[1])
