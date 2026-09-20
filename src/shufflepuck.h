/* shufflepuck.h — moteur de Shufflepuck Cafe, retro-ingenierie de la version
 * Atari ST (Broderbund / Loriciel, 1989).
 *
 * Toutes les constantes de ce fichier sont extraites du binaire d'origine et
 * documentees dans PHYSICS.md. Aucune n'est inventee ni ajustee a l'oreille.
 */
#ifndef SHUFFLEPUCK_H
#define SHUFFLEPUCK_H

/* ---- Terrain ------------------------------------------------------------
 * Rectangle plat. La perspective est un effet d'affichage, pas de simulation.
 */
#define SP_MUR_X          226   /* murs lateraux, +/-                        */
#define SP_MUR_REFLEXION  452   /* 2 * SP_MUR_X, pour la reflexion miroir    */
#define SP_Y_JOUEUR       295   /* ligne de service du joueur                */
#define SP_Y_ADVERSAIRE  1205   /* ligne de service de l'adversaire          */
#define SP_Y_FOND        1500   /* reference de profondeur                   */

/* ---- Bornes de vitesse du palet ---------------------------------------- */
#define SP_PALET_DX_MAX   150
#define SP_PALET_DY_MAX   300

/* ---- Raquette du joueur ------------------------------------------------- */
#define SP_SOURIS_MAX      32   /* ecart souris retenu par image, +/-        */
#define SP_DEPL_MAX       200   /* deplacement apres courbe, +/-             */
#define SP_JOUEUR_Y_MIN     0
#define SP_JOUEUR_Y_MAX   300
#define SP_LIMITE_MUR     250   /* bornage des raquettes                     */

/* ---- Collision ---------------------------------------------------------- */
#define SP_POURCENT       100   /* denominateur des coefficients             */

/* ---- Projection --------------------------------------------------------- */
#define SP_PROJ_ECHELLE   411
#define SP_PROJ_RECUL     643
#define SP_ECRAN_CENTRE   160

/* ---- Audio -------------------------------------------------------------- */
#define SP_SON_BANQUE_JEU   0x100
#define SP_SON_REBOND_BASE  4    /* echantillons 4..25 selon la profondeur   */
#define SP_SON_REBOND_MAX   25
#define SP_SON_REBOND_PAS   68   /* Y / 68 choisit la bande                  */
#define SP_SON_FRAPPE       0x11A
#define SP_SON_VITRE_FORT   0x102
#define SP_SON_VITRE_DOUX   0x103
#define SP_VITRE_SEUIL      150  /* |dy| au-dela duquel l'impact est "fort"  */

/* ---- Vitre brisee ------------------------------------------------------- */
#define SP_ECLATS          13
#define SP_ECLAT_GRAVITE   12
#define SP_ECLAT_SOL      150

typedef struct {
    int x, y;        /* position sur le rectangle             */
    int dx, dy;      /* vitesse                               */
} SpPalet;

/* Bloc de parametres d'une raquette. Les huit coefficients sont des
 * pourcentages ; le jeu 2 s'applique quand l'adversaire n'est pas en train
 * de frapper (drapeau +$1A non nul), et annule alors tout transfert.
 */
typedef struct {
    int x, y;                /* +$00 +$02 */
    int vx, vy;              /* +$04 +$06 */
    int largeur;             /* +$08  demi-largeur = largeur/2 */
    int cxx, cyy, cxp, cyp;  /* +$0A..+$10  jeu 1 */
    int cxx2, cyy2, cxp2, cyp2; /* +$12..+$18  jeu 2 */
    int frappe;              /* +$1A  0 = frappe (transfert), 1 = passif */

    int x_min, x_max;        /* +$1E +$20  bornes de patrouille */
    int y_pres, y_loin;      /* +$22 +$24  mesures depuis SP_Y_FOND */
    int vr_droite, vr_gauche, vr_loin, vr_pres; /* +$26..+$2C */
    int pas_gauche, pas_droite, pas_arriere, pas_avant; /* +$2E..+$34 */
    int pas_frappe_x, pas_frappe_y;  /* +$36 +$38 */
    int cible_x_min, cible_x_max;    /* +$42 +$44 */
    int cible_y_min, cible_y_max;    /* +$46 +$48 */
    int erreur_visee;        /* +$4A */
    int seuil_reaction;      /* +$4E  reagit quand Y > SP_Y_FOND - ce champ */
    int pas_simulation;      /* +$50  profondeur d'anticipation */
    const char *nom;         /* +$54  pointeur de nom */
} SpRaquette;

int  sp_borner(int min, int v, int max);
void sp_palet_avancer(SpPalet *p, void (*son_rebond)(int y));
void sp_collision(SpPalet *p, const SpRaquette *r);
void sp_joueur_souris(SpRaquette *j, int souris_dx, int souris_dy);
int  sp_projeter_x(int x, int y);
int  sp_son_rebond(int y);

extern const SpRaquette sp_adversaires[9];
extern const SpRaquette sp_joueur_defaut;

#endif
