/* ia.c — intelligence artificielle des adversaires.
 * Transcription du 68000 d'origine. Voir PHYSICS.md.
 */
#include "shufflepuck.h"

/* Etats de la machine ($1B598). Chaque etat positionne le drapeau
 * `frappe`, qui decide si la raquette transmet sa puissance au palet.
 */
enum { SP_ANTICIPE = 0, SP_POURSUIT, SP_ARRIVE, SP_FRAPPE_A,
       SP_RECENTRE, SP_FRAPPE_B, SP_SERVICE };

/* --- $010802 : patrouille ------------------------------------------------
 * Deplacement a vitesse constante, rebond sur les bornes de la zone.
 * Chaque borne impose sa propre vitesse de repart.
 */
void sp_ia_patrouille(SpRaquette *r)
{
    int demi = r->largeur / 2;
    int nx = r->x + r->vx;
    int ny = r->y + r->vy;

    if (nx >= r->x_max || nx + demi >= SP_LIMITE_MUR) {
        if (r->vx >= 0) { nx = r->x_max; r->vx = -r->vr_droite; }
    } else if (nx <= r->x_min || nx - demi <= -SP_LIMITE_MUR) {
        if (r->vx <= 0) { nx = r->x_min; r->vx =  r->v_attente_x; }
    }

    if (ny >= SP_Y_FOND - r->y_pres) {
        if (r->vy >= 0) { ny = SP_Y_FOND - r->y_pres; r->vy = -r->vr_pres; }
    } else if (ny <= SP_Y_FOND - r->y_loin) {
        if (r->vy <= 0) { ny = SP_Y_FOND - r->y_loin; r->vy =  r->v_attente_y; }
    }
    r->x = nx;
    r->y = ny;
}

/* --- $01096C : recentrage ------------------------------------------------
 * Oriente la vitesse vers le milieu de la zone, puis patrouille.
 */
void sp_ia_recentre(SpRaquette *r)
{
    int centre_x = (r->x_min + r->x_max) / 2;
    int centre_y = (r->y_pres + r->y_loin) / 2;

    r->vx = (r->x > centre_x) ? -r->vr_droite : r->v_attente_x;
    r->vy = (SP_Y_FOND - r->y > centre_y) ? r->v_attente_y : -r->vr_pres;
    sp_ia_patrouille(r);
}

/* --- $010A02 : anticipation ----------------------------------------------
 * L'adversaire rejoue la VRAIE physique en avance rapide pour savoir ou le
 * palet arrivera. Sa prediction est donc exacte par construction ; toute la
 * difficulte vient de l'erreur de visee, du seuil de reaction et de la
 * profondeur d'anticipation.
 *
 * Renvoie 1 si une cible a ete calculee, 0 sinon.
 */
int sp_ia_anticipe(const SpRaquette *r, const SpPalet *palet,
                   int (*alea)(int min, int max),
                   int *cible_x, int *cible_y)
{
    SpPalet sim = *palet;
    int n;

    if (palet->dy <= 0) return 0;                       /* il s'eloigne */
    if (palet->y <= SP_Y_FOND - r->seuil_reaction) return 0;  /* trop tot */

    sim.x += alea(-r->erreur_visee, r->erreur_visee);   /* visee imparfaite */

    for (n = 0; n < r->pas_simulation; n++)
        sp_palet_avancer(&sim, 0);

    *cible_x = sim.x;
    *cible_y = sim.y;
    return 1;
}

/* --- $010AB6 : poursuite -------------------------------------------------
 * Avance vers la cible par pas bornes. Une fois arrivee, la raquette se
 * decale au hasard : c'est ce qui fait varier ses angles de renvoi.
 */
int sp_ia_poursuit(SpRaquette *r, int cible_x, int cible_y,
                   int (*alea)(int min, int max),
                   int *frappe_x, int *frappe_y)
{
    int nx = r->x + sp_borner(-r->pas_gauche,  cible_x - r->x, r->v_attaque);
    int ny = r->y + sp_borner(-r->pas_avant,   cible_y - r->y, r->pas_arriere);

    if (nx == r->x && ny == r->y) {          /* arrivee */
        *frappe_x = cible_x + alea(r->disp_x_min, r->disp_x_max);
        *frappe_y = cible_y + alea(r->disp_y_min, r->disp_y_max);
        return 1;
    }
    r->x = nx;
    r->y = ny;
    return 0;
}

/* --- $010BCE / $010C7C : frappe ------------------------------------------
 * Approche finale, a vitesse propre et symetrique. C'est le seul etat ou la
 * raquette transmet sa puissance (drapeau `frappe` a 0).
 */
void sp_ia_frappe(SpRaquette *r, int vers_x, int vers_y)
{
    r->x += sp_borner(-r->v_defense, vers_x - r->x, r->v_defense);
    r->y += sp_borner(-r->pas_frappe_y, vers_y - r->y, r->pas_frappe_y);
    r->frappe = 0;
}

/* --- $0110BA : l'ivresse de Lexan ----------------------------------------
 * Appelee apres un point, sur tirage a pile ou face, et UNIQUEMENT si
 * l'adversaire courant est Lexan.
 *
 * Trois coefficients distincts : il s'affaiblit, il titube, il rate.
 * Modele verifie a l'entier pres sur 19 champs (voir PHYSICS.md).
 */
static int sp_degrader(int v, int num)
{
    long p = (long)v * num;
    return (int)(p >= 0 ? p / 100 : -((-p) / 100));   /* DIVS tronque vers zero */
}

void sp_lexan_boit(SpRaquette *r)
{
    r->reflex_x  = sp_degrader(r->reflex_x,  82);  r->reflex_y  = sp_degrader(r->reflex_y,  82);
    r->accel_x  = sp_degrader(r->accel_x,  82);  r->accel_y  = sp_degrader(r->accel_y,  82);
    r->reflex_x2 = sp_degrader(r->reflex_x2, 82);  r->reflex_y2 = sp_degrader(r->reflex_y2, 82);

    r->vr_droite = sp_degrader(r->vr_droite, 82);
    r->v_attente_x = sp_degrader(r->v_attente_x, 82);
    r->v_attente_y   = sp_degrader(r->v_attente_y,   82);
    r->vr_pres   = sp_degrader(r->vr_pres,   82);

    r->pas_gauche  = sp_degrader(r->pas_gauche,  82);
    r->v_attaque  = sp_degrader(r->v_attaque,  82);
    r->pas_arriere = sp_degrader(r->pas_arriere, 82);
    r->pas_avant   = sp_degrader(r->pas_avant,   82);

    r->v_defense = sp_degrader(r->v_defense, 82);
    r->pas_frappe_y = sp_degrader(r->pas_frappe_y, 82);

    r->x_min = sp_degrader(r->x_min, 107);   /* sa zone s'elargit : il titube */
    r->x_max = sp_degrader(r->x_max, 107);
    r->erreur_visee = sp_degrader(r->erreur_visee, 105);  /* il vise moins bien */
}

/* --- $010D44 : cible de service ------------------------------------------
 * Biff ajuste sa cible a l'ecart de score ; les autres tirent au hasard
 * dans leurs bornes. Bejin est traitee a part (tell sonore).
 */
void sp_ia_service(const SpRaquette *r, int est_biff, int ecart_score,
                   int (*alea)(int min, int max), int *cx, int *cy)
{
    if (est_biff) {
        int pas = sp_borner(-10, ecart_score, 10) + 10;   /* 0..20 */
        *cx = r->cible_x_max * pas / 20;
        if (alea(0, 1)) *cx = -*cx;
        *cy = r->cible_y_min
            + (r->cible_y_max - r->cible_y_min) * pas / 20
            + SP_Y_ADVERSAIRE;
    } else {
        *cx = alea(r->cible_x_min, r->cible_x_max);
        *cy = alea(r->cible_y_min, r->cible_y_max) + SP_Y_ADVERSAIRE;
    }
}
