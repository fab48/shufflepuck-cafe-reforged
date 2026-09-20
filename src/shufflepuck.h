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

/* Bloc de parametres d'une raquette : 86 octets, image exacte de la memoire.
 *
 * La nomenclature vient des AUTEURS, pas de moi : Loriciel a laisse dans le
 * binaire son editeur de reglages (table 0x01A118, voir tools/editeur.py),
 * ou chaque champ porte son libelle francais et ses bornes. Les champs que
 * cet editeur nomme sont marques (auteurs) ; les autres viennent de la
 * lecture du code et restent mes noms.
 *
 * Les deux jeux de coefficients confirment la formule de collision : un
 * terme de REFLEXION applique a la vitesse du palet, un terme
 * d'ACCELERATION applique a la vitesse de la raquette. Le jeu 2 s'applique
 * quand l'adversaire n'est pas en train de frapper (drapeau +$1A non nul).
 */
typedef struct {
    int x, y;                /* +$00 +$02 */
    int vx, vy;              /* +$04 +$06 */
    int largeur;             /* +$08  demi-largeur = largeur/2            */

    /* jeu 1 — bornes de l'editeur : reflexion 0..100, acceleration 0..200 */
    int reflex_x;            /* +$0A  "reflexion laterale"      (auteurs) */
    int reflex_y;            /* +$0C  "reflexion transversale"  (auteurs) */
    int accel_x;             /* +$0E  "acceleration laterale"   (auteurs) */
    int accel_y;             /* +$10  "acceleration transversale" (auteurs) */
    /* jeu 2 — memes libelles, second jeu */
    int reflex_x2;           /* +$12 */
    int reflex_y2;           /* +$14 */
    int accel_x2;            /* +$16 */
    int accel_y2;            /* +$18 */

    int frappe;              /* +$1A  0 = frappe (transfert), 1 = passif  */
    int _1c;                 /* +$1C  inutilise dans tous les blocs lus   */

    int x_min, x_max;        /* +$1E +$20  "debattement horizontal" 0..250 */
    int y_pres, y_loin;      /* +$22 +$24  mesures depuis SP_Y_FOND        */

    /* Vitesses d'attente. L'editeur n'expose qu'un representant par axe ;
     * les deux autres viennent du code, qui choisit selon la direction.   */
    int vr_droite;           /* +$26 */
    int v_attente_x;         /* +$28  "vitesse attente horizontale" 0..100 (auteurs) */
    int v_attente_y;         /* +$2A  "vitesse attente verticale"   0..100 (auteurs) */
    int vr_pres;             /* +$2C */

    int pas_gauche;          /* +$2E */
    int v_attaque;           /* +$30  "vitesse d'attaque"  1..200  (auteurs) */
    int pas_arriere;         /* +$32 */
    int pas_avant;           /* +$34 */
    int v_defense;           /* +$36  "vitesse de defense" 1..200  (auteurs) */
    int pas_frappe_y;        /* +$38 */

    /* Dispersion du point de frappe, puis zone visee. L'editeur nomme les
     * quatre paires et donne leurs bornes : X dans -250..250, Y dans 0..300. */
    int disp_x_min, disp_x_max;   /* +$3A +$3C  "gauche-droite min/max" (auteurs) */
    int disp_y_min, disp_y_max;   /* +$3E +$40  "avant-arriere min/max" (auteurs) */
    int cible_x_min, cible_x_max; /* +$42 +$44  "gauche-droite min/max" (auteurs) */
    int cible_y_min, cible_y_max; /* +$46 +$48  "avant-arriere min/max" (auteurs) */

    int erreur_visee;        /* +$4A */
    int _4c;                 /* +$4C */
    int seuil_reaction;      /* +$4E  reagit quand Y > SP_Y_FOND - ce champ */
    int pas_simulation;      /* +$50  profondeur d'anticipation             */
    const char *nom;         /* +$52  pointeur de nom — les 4 derniers octets
                              *       du bloc de 86, verifie sur les 9 blocs */
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
