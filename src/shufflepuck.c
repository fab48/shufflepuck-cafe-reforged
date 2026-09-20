/* shufflepuck.c — moteur de Shufflepuck Cafe.
 * Transcription lisible du code 68000 d'origine (Atari ST, 1989).
 * Voir PHYSICS.md pour la provenance de chaque formule.
 */
#include "shufflepuck.h"

/* $00FDEC — bornage a trois arguments. */
int sp_borner(int min, int v, int max)
{
    if (v < min) return min;
    if (v > max) return max;
    return v;
}

/* $010466 — un pas de physique du palet.
 * Les vitesses sont bornees AVANT l'integration, comme dans l'original.
 */
void sp_palet_avancer(SpPalet *p, void (*son_rebond)(int y))
{
    p->dx = sp_borner(-SP_PALET_DX_MAX, p->dx, SP_PALET_DX_MAX);
    p->dy = sp_borner(-SP_PALET_DY_MAX, p->dy, SP_PALET_DY_MAX);

    p->x += p->dx;
    p->y += p->dy;

    if (p->x < -SP_MUR_X) {
        if (son_rebond) son_rebond(p->y);
        p->dx = -p->dx;
        p->x  = -SP_MUR_REFLEXION - p->x;   /* reflexion miroir */
    } else if (p->x > SP_MUR_X) {
        if (son_rebond) son_rebond(p->y);
        p->dx = -p->dx;
        p->x  = SP_MUR_REFLEXION - p->x;
    }
}

/* $00FEEC — reponse a la collision. Le coeur du ressenti.
 *
 *   dx' = ( dx * Cxx  +  raquette.vx * Cxp ) / 100
 *   dy' = ( raquette.vy * Cyp  -  dy * Cyy ) / 100
 *
 * Le signe moins devant dy produit l'inversion : le palet repart.
 * Quand la raquette n'est pas en phase de frappe, le jeu 2 s'applique et
 * annule le transfert de puissance (Cxp2 = Cyp2 = 0 pour tous les adversaires).
 */
void sp_collision(SpPalet *p, const SpRaquette *r)
{
    int cxx, cyy, cxp, cyp;

    if (r->frappe) {                 /* drapeau +$1A non nul */
        cxx = r->cxx2; cyy = r->cyy2; cxp = r->cxp2; cyp = r->cyp2;
    } else {
        cxx = r->cxx;  cyy = r->cyy;  cxp = r->cxp;  cyp = r->cyp;
    }

    p->dx = (p->dx * cxx + r->vx * cxp) / SP_POURCENT;
    p->dy = (r->vy * cyp - p->dy * cyy) / SP_POURCENT;

    p->dx = sp_borner(-SP_PALET_DX_MAX, p->dx, SP_PALET_DX_MAX);
    p->dy = sp_borner(-SP_PALET_DY_MAX, p->dy, SP_PALET_DY_MAX);
}

/* $00FB7A — souris vers raquette du joueur.
 *
 * La courbe d'acceleration  d' = d + d*|d|/8  donne du 1:1 sur les petits
 * gestes et une amplification x5 a l'ecart maximal.
 *
 * Point essentiel : la vitesse est le deplacement REEL, calcule apres
 * bornage. Raquette contre un mur => vitesse nulle => aucune puissance
 * transmise a la collision. L'original ne le programme nulle part : cela
 * decoule de cet ordre de calcul.
 */
void sp_joueur_souris(SpRaquette *j, int souris_dx, int souris_dy)
{
    int dx = sp_borner(-SP_SOURIS_MAX, souris_dx, SP_SOURIS_MAX);
    int dy = sp_borner(-SP_SOURIS_MAX, souris_dy, SP_SOURIS_MAX);
    int demi = j->largeur / 2;
    int nx, ny;

    /* Courbe d'acceleration. L'ORDRE DES OPERATIONS COMPTE : l'original
     * calcule |d|/2 d'abord (decalage arithmetique), puis multiplie, puis
     * divise par 4. Regrouper en d*|d|/8 donne un resultat different en
     * arithmetique entiere -- verifie : pour d=5, 7 et non 8.
     *
     * Reserve : l'original utilise MULU (multiplication non signee) sur un
     * operande potentiellement negatif, puis DIVS. Le comportement aux
     * valeurs extremes n'a pas ete verifie contre le materiel.
     */
    dx += dx * ((dx < 0 ? -dx : dx) / 2) / 4;
    dy += dy * ((dy < 0 ? -dy : dy) / 2) / 4;
    dx = sp_borner(-SP_DEPL_MAX, dx, SP_DEPL_MAX);
    dy = sp_borner(-SP_DEPL_MAX, dy, SP_DEPL_MAX);

    nx = sp_borner(demi - SP_LIMITE_MUR, j->x + dx, SP_LIMITE_MUR - demi);
    ny = sp_borner(SP_JOUEUR_Y_MIN, j->y - dy, SP_JOUEUR_Y_MAX);  /* Y inverse */

    j->vx = nx - j->x;
    j->vy = ny - j->y;
    j->x  = nx;
    j->y  = ny;
}

/* $DB9C — projection en perspective, abscisse.
 * Verifiee : le centre tombe toujours sur 160, la table passe de 199 px
 * pres du joueur a 101 px au fond.
 */
int sp_projeter_x(int x, int y)
{
    return x * SP_PROJ_ECHELLE / (y + SP_PROJ_RECUL) + SP_ECRAN_CENTRE;
}

/* $11486 — choix de l'echantillon de rebond selon la profondeur.
 * Le ST ne transpose pas : 22 echantillons distincts sont pre-enregistres.
 */
int sp_son_rebond(int y)
{
    int n = sp_borner(SP_SON_REBOND_BASE,
                      y / SP_SON_REBOND_PAS + SP_SON_REBOND_BASE,
                      SP_SON_REBOND_MAX);
    return SP_SON_BANQUE_JEU | n;
}

/* ---- Donnees extraites de la table $19D14 (pas de 86 octets) -------------
 * Ordre etabli par le pointeur de nom en +$54, et NON par l'ordre du cafe.
 *
 * Ce bloc est GENERE automatiquement depuis le dump memoire du jeu par
 * tools/gen_table.py : aucune valeur n'est recopiee a la main.
 *
 * Initialiseurs designes : chaque valeur porte le nom de son champ, ce qui
 * rend la table immune a tout changement d'ordre dans la structure.
 */
const SpRaquette sp_adversaires[9] = {
  { /* 0 — Skip */
    .nom = "Skip",
    .largeur = 100, .cxx = 17, .cyy = 20, .cxp = 28, .cyp = 34, .cxx2 = 17,
    .cyy2 = 20, .cxp2 = 0, .cyp2 = 0, .x_min = -87, .x_max = -11,
    .y_pres = 84, .y_loin = 163, .vr_droite = 10, .vr_gauche = 10,
    .vr_loin = 33, .vr_pres = 34, .pas_gauche = 8, .pas_droite = 8,
    .pas_arriere = 9, .pas_avant = 6, .pas_frappe_x = 13,
    .pas_frappe_y = 14, .disp_x_min = -60, .disp_x_max = 66,
    .disp_y_min = 34, .disp_y_max = 30, .cible_x_min = -18,
    .cible_x_max = 15, .cible_y_min = 88, .cible_y_max = 120,
    .erreur_visee = 50, .seuil_reaction = 1200, .pas_simulation = 92,
  },
  { /* 1 — Vinnie */
    .nom = "Vinnie",
    .largeur = 100, .cxx = 20, .cyy = 30, .cxp = 41, .cyp = 80, .cxx2 = 20,
    .cyy2 = 30, .cxp2 = 0, .cyp2 = 0, .x_min = -168, .x_max = 189,
    .y_pres = 0, .y_loin = 171, .vr_droite = 2, .vr_gauche = 2,
    .vr_loin = 5, .vr_pres = 5, .pas_gauche = 26, .pas_droite = 29,
    .pas_arriere = 26, .pas_avant = 32, .pas_frappe_x = 3,
    .pas_frappe_y = 5, .disp_x_min = -151, .disp_x_max = 158,
    .disp_y_min = 193, .disp_y_max = 293, .cible_x_min = -50,
    .cible_x_max = 11, .cible_y_min = 84, .cible_y_max = 127,
    .erreur_visee = 5, .seuil_reaction = 1200, .pas_simulation = 88,
  },
  { /* 2 — Visine */
    .nom = "Visine",
    .largeur = 100, .cxx = 25, .cyy = 40, .cxp = 28, .cyp = 23, .cxx2 = 25,
    .cyy2 = 40, .cxp2 = 0, .cyp2 = 0, .x_min = -136, .x_max = 144,
    .y_pres = 40, .y_loin = 251, .vr_droite = 122, .vr_gauche = 116,
    .vr_loin = 141, .vr_pres = 149, .pas_gauche = 74, .pas_droite = 77,
    .pas_arriere = 48, .pas_avant = 37, .pas_frappe_x = 139,
    .pas_frappe_y = 145, .disp_x_min = -55, .disp_x_max = 58,
    .disp_y_min = 45, .disp_y_max = 93, .cible_x_min = -230,
    .cible_x_max = 1, .cible_y_min = 26, .cible_y_max = 59,
    .erreur_visee = 0, .seuil_reaction = 380, .pas_simulation = 92,
  },
  { /* 3 — Lexan */
    .nom = "Lexan",
    .largeur = 100, .cxx = 30, .cyy = 50, .cxp = 72, .cyp = 101, .cxx2 = 30,
    .cyy2 = 50, .cxp2 = 0, .cyp2 = 0, .x_min = -136, .x_max = 23,
    .y_pres = 58, .y_loin = 171, .vr_droite = 22, .vr_gauche = 42,
    .vr_loin = 43, .vr_pres = 61, .pas_gauche = 120, .pas_droite = 128,
    .pas_arriere = 113, .pas_avant = 106, .pas_frappe_x = 89,
    .pas_frappe_y = 88, .disp_x_min = -149, .disp_x_max = 155,
    .disp_y_min = 189, .disp_y_max = 288, .cible_x_min = -86,
    .cible_x_max = -5, .cible_y_min = 103, .cible_y_max = 206,
    .erreur_visee = 34, .seuil_reaction = 1200, .pas_simulation = 70,
  },
  { /* 4 — Nerual */
    .nom = "Nerual",
    .largeur = 60, .cxx = 97, .cyy = 100, .cxp = 70, .cyp = 130, .cxx2 = 97,
    .cyy2 = 100, .cxp2 = 0, .cyp2 = 0, .x_min = -220, .x_max = 220,
    .y_pres = 0, .y_loin = 290, .vr_droite = 4, .vr_gauche = 5,
    .vr_loin = 4, .vr_pres = 4, .pas_gauche = 58, .pas_droite = 53,
    .pas_arriere = 82, .pas_avant = 61, .pas_frappe_x = 161,
    .pas_frappe_y = 238, .disp_x_min = 0, .disp_x_max = 0, .disp_y_min = 0,
    .disp_y_max = 0, .cible_x_min = -11, .cible_x_max = 13,
    .cible_y_min = 22, .cible_y_max = 55, .erreur_visee = 0,
    .seuil_reaction = 1200, .pas_simulation = 78,
  },
  { /* 5 — Eneg */
    .nom = "Eneg",
    .largeur = 80, .cxx = 15, .cyy = 30, .cxp = 100, .cyp = 100, .cxx2 = 15,
    .cyy2 = 30, .cxp2 = 0, .cyp2 = 0, .x_min = -164, .x_max = -64,
    .y_pres = 89, .y_loin = 171, .vr_droite = 3, .vr_gauche = 3,
    .vr_loin = 3, .vr_pres = 2, .pas_gauche = 123, .pas_droite = 65,
    .pas_arriere = 71, .pas_avant = 77, .pas_frappe_x = 13,
    .pas_frappe_y = 14, .disp_x_min = -151, .disp_x_max = 158,
    .disp_y_min = 193, .disp_y_max = 293, .cible_x_min = -87,
    .cible_x_max = 67, .cible_y_min = 136, .cible_y_max = 231,
    .erreur_visee = 5, .seuil_reaction = 1200, .pas_simulation = 80,
  },
  { /* 6 — Bejin */
    .nom = "Bejin",
    .largeur = 50, .cxx = 10, .cyy = 37, .cxp = 49, .cyp = 102, .cxx2 = 10,
    .cyy2 = 37, .cxp2 = 0, .cyp2 = 0, .x_min = 0, .x_max = 0, .y_pres = 0,
    .y_loin = 0, .vr_droite = 2, .vr_gauche = 3, .vr_loin = 10,
    .vr_pres = 10, .pas_gauche = 69, .pas_droite = 72, .pas_arriere = 83,
    .pas_avant = 83, .pas_frappe_x = 13, .pas_frappe_y = 14,
    .disp_x_min = -156, .disp_x_max = 165, .disp_y_min = 202,
    .disp_y_max = 306, .cible_x_min = 0, .cible_x_max = 0,
    .cible_y_min = 49, .cible_y_max = 49, .erreur_visee = 0,
    .seuil_reaction = 1200, .pas_simulation = 80,
  },
  { /* 7 — Biff */
    .nom = "Biff",
    .largeur = 100, .cxx = 13, .cyy = 40, .cxp = 72, .cyp = 184, .cxx2 = 13,
    .cyy2 = 40, .cxp2 = 0, .cyp2 = 0, .x_min = -77, .x_max = 81,
    .y_pres = 124, .y_loin = 274, .vr_droite = 10, .vr_gauche = 10,
    .vr_loin = 10, .vr_pres = 10, .pas_gauche = 66, .pas_droite = 64,
    .pas_arriere = 63, .pas_avant = 64, .pas_frappe_x = 13,
    .pas_frappe_y = 14, .disp_x_min = -152, .disp_x_max = 159,
    .disp_y_min = 194, .disp_y_max = 294, .cible_x_min = 0,
    .cible_x_max = 104, .cible_y_min = 84, .cible_y_max = 300,
    .erreur_visee = 0, .seuil_reaction = 1200, .pas_simulation = 91,
  },
  { /* 8 — Dc3 */
    .nom = "Dc3",
    .largeur = 100, .cxx = 15, .cyy = 16, .cxp = 15, .cyp = 16, .cxx2 = 15,
    .cyy2 = 16, .cxp2 = 0, .cyp2 = 0, .x_min = -200, .x_max = 200,
    .y_pres = 150, .y_loin = 150, .vr_droite = 3, .vr_gauche = 3,
    .vr_loin = 10, .vr_pres = 10, .pas_gauche = 17, .pas_droite = 17,
    .pas_arriere = 17, .pas_avant = 17, .pas_frappe_x = 14,
    .pas_frappe_y = 14, .disp_x_min = -156, .disp_x_max = 165,
    .disp_y_min = 202, .disp_y_max = 300, .cible_x_min = -86,
    .cible_x_max = 72, .cible_y_min = 109, .cible_y_max = 218,
    .erreur_visee = 0, .seuil_reaction = 1200, .pas_simulation = 92,
  },
};

/* Le joueur : seul a conserver un transfert de puissance dans le jeu 2
 * (70 / 140 au lieu de 0 / 0 chez tous les adversaires).
 */
const SpRaquette sp_joueur_defaut = {
    .nom = "Joueur", .y = 150, .largeur = 100,
    .cxx  = 50, .cyy  = 50, .cxp  = 70, .cyp  = 130,
    .cxx2 = 50, .cyy2 = 50, .cxp2 = 70, .cyp2 = 140,
};
