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
 * Ordre etabli par le pointeur de nom en +$54, et non par l'ordre du cafe.
 */
#define RAQ(nom_, l, a,b,c,d, xmin,xmax,ypres,yloin, \
            vrd,vrg,vrl,vrp, pg,pd,par,pav, pfx,pfy, \
            cxmin,cxmax,cymin,cymax, err, seuil, pas)                         \
    { 0,0,0,0, l, a,b,c,d, a,b,0,0, 0,                                        \
      xmin,xmax,ypres,yloin, vrd,vrg,vrl,vrp, pg,pd,par,pav, pfx,pfy,         \
      cxmin,cxmax,cymin,cymax, err, seuil, pas, nom_ }

const SpRaquette sp_adversaires[9] = {
 RAQ("Skip",  100, 17, 20, 28, 34,  -87,-11, 84,163,  10,10,33,34,
     8,8,9,6,      13,14,   -18, 15, 88,120,  50, 1200, 92),
 RAQ("Vinnie",100, 20, 30, 41, 80, -168,189,  0,171,   2, 2, 5, 5,
     26,29,26,32,   3, 5,   -50, 11, 84,127,   5, 1200, 88),
 RAQ("Visine",100, 25, 40, 28, 23, -136,144, 40,251, 122,116,141,149,
     74,77,48,37, 139,145,  -230,  1, 26, 59,   0,  380, 92),
 RAQ("Lexan", 100, 30, 50, 72,101, -136, 23, 58,171,  22,42,43,61,
     120,128,113,106, 89,88,  -86, -5,103,206,  34, 1200, 70),
 RAQ("Nerual", 60, 97,100, 70,130, -220,220,  0,290,   4, 5, 4, 4,
     58,53,61,82,  161,238,  -11, 13, 22, 55,   0, 1200, 78),
 RAQ("Eneg",   80, 15, 30,100,100, -164,-64, 89,171,   3, 3, 3, 2,
     123,65,77,71, 13,14,    -87, 67,136,231,   5, 1200, 80),
 RAQ("Bejin",  50, 10, 37, 49,102,    0,  0,  0,  0,   2, 3,10,10,
     69,72,83,83,  13,14,      0,  0, 49, 49,   0, 1200, 80),
 RAQ("Biff",  100, 13, 40, 72,184,  -77, 81,124,274,  10,10,10,10,
     66,64,64,63,  13,14,      0,104, 84,300,   0, 1200, 91),
 RAQ("Dc3",   100, 15, 16, 15, 16, -200,200,150,150,   3, 3,10,10,
     17,17,17,17,  14,14,    -86, 72,109,218,   0, 1200, 92),
};

/* Le joueur : seul a conserver un transfert de puissance dans le jeu 2
 * (70 / 140 au lieu de 0 / 0).
 */
const SpRaquette sp_joueur_defaut = {
    0, 150, 0, 0, 100,
    50, 50, 70, 130,
    50, 50, 70, 140,
    0,
    0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0, 0,0,0,0, 0, 0, 0, "Joueur"
};
