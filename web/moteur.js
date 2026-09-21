// moteur.js — physique et IA de Shufflepuck Cafe.
//
// Transcription directe de src/shufflepuck.c et src/ia.c, eux-memes
// transcrits du 68000 d'origine. Aucune formule n'est reecrite « en mieux » :
// la provenance de chacune est dans PHYSICS.md, et les ecarts d'arrondi
// changent le ressenti.
//
// Un point d'attention permanent : le 68000 divise en tronquant VERS ZERO
// (instruction DIVS). En JavaScript, `a / b` donne un flottant et `Math.floor`
// arrondit vers le bas — ce qui differe pour les negatifs. On passe donc
// partout par `div()`, qui tronque vers zero.

export const ETAT = Object.freeze({
  ANTICIPE: 0, POURSUIT: 1, ARRIVE: 2, FRAPPE_A: 3,
  RECENTRE: 4, FRAPPE_B: 5, SERVICE: 6,
});

/** Division entiere tronquee vers zero, comme DIVS. */
export function div(a, b) { return Math.trunc(a / b); }

/** $00FDEC — bornage a trois arguments. */
export function borner(min, v, max) {
  if (v < min) return min;
  if (v > max) return max;
  return v;
}

export class Moteur {
  /** @param m le manifeste exporte par tools/exporter_web.py */
  constructor(m) {
    this.k = m.moteur;
    this.table = m.table_adversaires;
    this.gabaritJoueur = m.joueur;
    this.alea = (min, max) => {
      // L'original tire dans [min, max]. Skip a disp_x = alea(34, 30),
      // borne haute INFERIEURE a la borne basse : c'est un bug d'origine,
      // conserve tel quel (voir PHYSICS.md). On ne le « corrige » pas.
      const n = max - min + 1;
      if (n <= 0) return min + div(Math.floor(Math.random() * 0x8000), n || -1);
      return min + Math.floor(Math.random() * n);
    };
    this.reinitialiser(0);
  }

  reinitialiser(indexAdversaire) {
    const k = this.k;
    const g = this.gabaritJoueur;
    this.joueur = {
      x: 0, y: k.y_joueur, vx: 0, vy: 0,
      largeur: g.largeur, frappe: 0,
      reflex_x: g.reflex_x, reflex_y: g.reflex_y,
      accel_x: g.accel_x, accel_y: g.accel_y,
      reflex_x2: g.reflex_x2, reflex_y2: g.reflex_y2,
      accel_x2: g.accel_x2, accel_y2: g.accel_y2,
    };
    this.adversaire = Object.assign({ x: 0, vx: 0, vy: 0, frappe: 1 },
                                    this.table[indexAdversaire]);
    // Sa zone de patrouille est [y_fond - y_loin, y_fond - y_pres] : pour
    // Skip, 1337 a 1416. SP_Y_ADVERSAIRE (1205) est sa ligne de SERVICE,
    // pas sa position de jeu. On le place au milieu de sa zone.
    this.adversaire.y = k.y_fond - div(this.adversaire.y_pres + this.adversaire.y_loin, 2);
    this.adversaire.x = div(this.adversaire.x_min + this.adversaire.x_max, 2);
    this.index = indexAdversaire;
    this.palet = { x: 0, y: k.y_joueur, dx: 0, dy: 0 };
    this.etat = ETAT.SERVICE;
    this.cible = { x: 0, y: 0 };
    this.frappeVers = { x: 0, y: 0 };
    this.scores = [0, 0];
    this.enJeu = false;
    this.rebonds = [];          // profondeurs des rebonds de l'image courante
  }

  // --- $010466 : un pas de physique du palet -------------------------------
  // Les vitesses sont bornees AVANT l'integration, comme dans l'original.
  avancerPalet(p, surRebond) {
    const k = this.k;
    p.dx = borner(-k.palet_dx_max, p.dx, k.palet_dx_max);
    p.dy = borner(-k.palet_dy_max, p.dy, k.palet_dy_max);
    p.x += p.dx;
    p.y += p.dy;
    if (p.x < -k.mur_x) {
      if (surRebond) surRebond(p.y);
      p.dx = -p.dx;
      p.x = -k.mur_reflexion - p.x;       // reflexion miroir
    } else if (p.x > k.mur_x) {
      if (surRebond) surRebond(p.y);
      p.dx = -p.dx;
      p.x = k.mur_reflexion - p.x;
    }
  }

  // --- $00FEEC : reponse a la collision ------------------------------------
  //   dx' = ( dx * reflexion_x + raquette.vx * acceleration_x ) / 100
  //   dy' = ( raquette.vy * acceleration_y - dy * reflexion_y ) / 100
  // Le signe moins devant dy produit l'inversion : le palet repart.
  collision(p, r) {
    const k = this.k;
    const rx = r.frappe ? r.reflex_x2 : r.reflex_x;
    const ry = r.frappe ? r.reflex_y2 : r.reflex_y;
    const ax = r.frappe ? r.accel_x2 : r.accel_x;
    const ay = r.frappe ? r.accel_y2 : r.accel_y;
    p.dx = div(p.dx * rx + r.vx * ax, k.pourcent);
    p.dy = div(r.vy * ay - p.dy * ry, k.pourcent);
    p.dx = borner(-k.palet_dx_max, p.dx, k.palet_dx_max);
    p.dy = borner(-k.palet_dy_max, p.dy, k.palet_dy_max);
  }

  // --- $00FB7A : souris vers raquette du joueur ----------------------------
  // La vitesse est le deplacement REEL, calcule APRES bornage : raquette
  // contre un mur => vitesse nulle => aucune puissance transmise. L'original
  // ne le programme nulle part, cela decoule de cet ordre de calcul.
  raquetteJoueur(j, sourisDx, sourisDy) {
    const k = this.k;
    let dx = borner(-k.souris_max, sourisDx, k.souris_max);
    let dy = borner(-k.souris_max, sourisDy, k.souris_max);
    const demi = div(j.largeur, 2);

    // Courbe d'acceleration. L'ORDRE COMPTE : |d|/2 d'abord, puis la
    // multiplication, puis /4. Regrouper en d*|d|/8 donne un entier
    // different (pour d=5 : 7 et non 8).
    dx += div(dx * div(Math.abs(dx), 2), 4);
    dy += div(dy * div(Math.abs(dy), 2), 4);
    dx = borner(-k.depl_max, dx, k.depl_max);
    dy = borner(-k.depl_max, dy, k.depl_max);

    const nx = borner(demi - k.limite_mur, j.x + dx, k.limite_mur - demi);
    const ny = borner(this.k.y_joueur - 120, j.y - dy, this.k.y_joueur + 120);
    j.vx = nx - j.x;
    j.vy = ny - j.y;
    j.x = nx;
    j.y = ny;
  }

  // --- $010802 : patrouille ------------------------------------------------
  patrouille(r) {
    const k = this.k;
    const demi = div(r.largeur, 2);
    let nx = r.x + r.vx;
    let ny = r.y + r.vy;
    if (nx >= r.x_max || nx + demi >= k.limite_mur) {
      if (r.vx >= 0) { nx = r.x_max; r.vx = -r.vr_droite; }
    } else if (nx <= r.x_min || nx - demi <= -k.limite_mur) {
      if (r.vx <= 0) { nx = r.x_min; r.vx = r.v_attente_x; }
    }
    if (ny >= k.y_fond - r.y_pres) {
      if (r.vy >= 0) { ny = k.y_fond - r.y_pres; r.vy = -r.vr_pres; }
    } else if (ny <= k.y_fond - r.y_loin) {
      if (r.vy <= 0) { ny = k.y_fond - r.y_loin; r.vy = r.v_attente_y; }
    }
    r.x = nx;
    r.y = ny;
  }

  // --- $01096C : recentrage ------------------------------------------------
  recentre(r) {
    const k = this.k;
    const cx = div(r.x_min + r.x_max, 2);
    const cy = div(r.y_pres + r.y_loin, 2);
    r.vx = (r.x > cx) ? -r.vr_droite : r.v_attente_x;
    r.vy = (k.y_fond - r.y > cy) ? r.v_attente_y : -r.vr_pres;
    this.patrouille(r);
  }

  // --- $010A02 : anticipation ----------------------------------------------
  // L'adversaire rejoue la VRAIE physique en avance rapide. Sa prediction est
  // donc exacte par construction ; la difficulte vient de l'erreur de visee,
  // du seuil de reaction et de la profondeur d'anticipation.
  anticipe(r, palet) {
    const k = this.k;
    if (palet.dy <= 0) return null;                       // il s'eloigne
    if (palet.y <= k.y_fond - r.seuil_reaction) return null;  // trop tot
    const sim = Object.assign({}, palet);
    sim.x += this.alea(-r.erreur_visee, r.erreur_visee);
    for (let n = 0; n < r.pas_simulation; n++) this.avancerPalet(sim, null);
    return { x: sim.x, y: sim.y };
  }

  // --- $010AB6 : poursuite -------------------------------------------------
  // RECONSTRUCTION : le bornage de la cible dans la zone de l'adversaire
  // n'est pas lu dans le code d'origine. Il est ajoute ici parce que sans
  // lui la raquette derive indefiniment hors de la table. La routine de
  // deplacement elle-meme, en revanche, est transcrite.
  poursuit(r, cibleBrute) {
    const k = this.k;
    const demi = div(r.largeur, 2);
    const cible = {
      x: borner(Math.min(r.x_min, r.x_max), cibleBrute.x, Math.max(r.x_min, r.x_max)),
      y: borner(k.y_fond - r.y_loin, cibleBrute.y, k.y_fond - r.y_pres),
    };
    cible.x = borner(demi - k.limite_mur, cible.x, k.limite_mur - demi);
    const nx = r.x + borner(-r.pas_gauche, cible.x - r.x, r.v_attaque);
    const ny = r.y + borner(-r.pas_avant, cible.y - r.y, r.pas_arriere);
    if (nx === r.x && ny === r.y) {
      return {
        x: cible.x + this.alea(r.disp_x_min, r.disp_x_max),
        y: cible.y + this.alea(r.disp_y_min, r.disp_y_max),
      };
    }
    r.x = nx;
    r.y = ny;
    return null;
  }

  // RECONSTRUCTION. La zone de patrouille (+$1E/+$20 en X, +$22/+$24 en Y)
  // est lue dans le code, et c'est la seule borne connue pour la raquette
  // adverse. On l'applique apres CHAQUE mouvement : sans cela, la frappe,
  // qui vise une cible dispersee au hasard, emmene la raquette hors de la
  // table. Le code d'origine contient forcement l'equivalent, je ne l'ai pas
  // encore trouve.
  contraindre(r) {
    const k = this.k;
    const demi = div(r.largeur, 2);
    const xa = Math.min(r.x_min, r.x_max), xb = Math.max(r.x_min, r.x_max);
    r.x = borner(Math.max(xa, demi - k.limite_mur), r.x,
                 Math.min(xb, k.limite_mur - demi));
    r.y = borner(k.y_fond - r.y_loin, r.y, k.y_fond - r.y_pres);
  }

  // --- $010BCE / $010C7C : frappe ------------------------------------------
  // Seul etat ou la raquette transmet sa puissance (drapeau `frappe` a 0).
  frappe(r, vers) {
    r.x += borner(-r.v_defense, vers.x - r.x, r.v_defense);
    r.y += borner(-r.pas_frappe_y, vers.y - r.y, r.pas_frappe_y);
    r.frappe = 0;
  }

  // --- $0110BA : l'ivresse de Lexan ----------------------------------------
  // Trois coefficients distincts : il s'affaiblit, il titube, il rate.
  // Verifie a l'entier pres sur 19 champs.
  lexanBoit(r) {
    const d = (v, num) => {
      const p = v * num;
      return p >= 0 ? div(p, 100) : -div(-p, 100);   // DIVS tronque vers zero
    };
    for (const c of ['reflex_x', 'reflex_y', 'accel_x', 'accel_y',
                     'reflex_x2', 'reflex_y2',
                     'vr_droite', 'v_attente_x', 'v_attente_y', 'vr_pres',
                     'pas_gauche', 'v_attaque', 'pas_arriere', 'pas_avant',
                     'v_defense', 'pas_frappe_y']) {
      r[c] = d(r[c], 82);
    }
    r.x_min = d(r.x_min, 107);          // la zone s'elargit : il titube
    r.x_max = d(r.x_max, 107);
    r.erreur_visee = d(r.erreur_visee, 105);   // et il rate davantage
  }

  // --- projection ----------------------------------------------------------
  // $DB9C : abscisse. Le centre tombe exactement sur 160 — confirme sur
  // l'image du terrain extraite de la disquette, sur chaque ligne.
  projeterX(x, y) {
    const k = this.k;
    return div(x * k.proj_echelle, y + k.proj_recul) + k.ecran_centre;
  }

  // $DBC2 : ordonnee. Le PREMIER argument est une HAUTEUR, pas une abscisse —
  // etabli par le site d'appel 0x00DC58, qui projette les quatre coins d'un
  // rectangle en passant deux hauteurs differentes et la meme profondeur.
  projeterY(hauteur, profondeur) {
    const p = this.k.proj_y;
    const t = div(profondeur * p.t_num, profondeur + p.t_den);
    return (p.sol - t) - (hauteur * (p.hauteur_num - t) >> p.hauteur_dec);
  }

  // $11486 : la sequence de rebond selon la profondeur. Le ST transpose :
  // un seul echantillon, rejoue a vingt-trois hauteurs.
  sequenceRebond(y) {
    const k = this.k;
    return borner(k.son_rebond_base, div(y, k.son_rebond_pas) + k.son_rebond_base, 26);
  }

  // --- la boucle -----------------------------------------------------------
  pas(sourisDx, sourisDy, servir) {
    const k = this.k;
    this.rebonds = [];
    const surRebond = (y) => this.rebonds.push(this.sequenceRebond(y));

    this.raquetteJoueur(this.joueur, sourisDx, sourisDy);

    if (!this.enJeu) {
      this.palet.x = this.joueur.x;
      this.palet.y = this.joueur.y;
      this.palet.dx = 0;
      this.palet.dy = 0;
      if (servir) { this.enJeu = true; this.palet.dy = 60; }
      this.iaAttente();
      return;
    }

    const avant = this.palet.y;
    this.avancerPalet(this.palet, surRebond);
    this.ia();

    // Contact avec une raquette : le palet traverse sa ligne et l'ecart en X
    // est dans la demi-largeur.
    const r = this.adversaire, j = this.joueur;
    if (this.palet.dy > 0 && avant <= r.y && this.palet.y >= r.y) {
      if (Math.abs(this.palet.x - r.x) <= div(r.largeur, 2)) {
        this.collision(this.palet, r);
        this.contact = 'adversaire';
      }
    } else if (this.palet.dy < 0 && avant >= j.y && this.palet.y <= j.y) {
      if (Math.abs(this.palet.x - j.x) <= div(j.largeur, 2)) {
        this.collision(this.palet, j);
        this.contact = 'joueur';
      }
    }

    // Point marque : le palet sort par un fond.
    if (this.palet.y > k.y_fond) { this.scores[0]++; this.apresPoint(); }
    else if (this.palet.y < 0) { this.scores[1]++; this.apresPoint(); }
  }

  apresPoint() {
    this.enJeu = false;
    this.etat = ETAT.SERVICE;
    // L'ivresse de Lexan : apres un point, a pile ou face, et uniquement lui.
    if (this.table[this.index].nom === 'Lexan' && Math.random() < 0.5) {
      this.lexanBoit(this.adversaire);
      this.ivresses = (this.ivresses || 0) + 1;
    }
  }

  iaAttente() {
    this.adversaire.frappe = 1;
    this.recentre(this.adversaire);
  }

  // RECONSTRUCTION. Le repartiteur 0x010EAA aiguille sur $1B598 et le
  // tableau des etats est etabli (voir PHYSICS.md), mais les TRANSITIONS
  // entre anticipation, poursuite et recentrage ne sont pas lues dans le
  // code. Celles-ci sont les miennes, choisies pour etre coherentes avec
  // les routines transcrites. A remplacer par la vraie logique le jour ou
  // elle sera lue.
  ia() {
    const r = this.adversaire;
    this.iaEtat(r);
    this.contraindre(r);
  }

  iaEtat(r) {
    switch (this.etat) {
      case ETAT.SERVICE:
      case ETAT.ANTICIPE: {
        r.frappe = 1;
        const c = this.anticipe(r, this.palet);
        if (c) { this.cible = c; this.etat = ETAT.POURSUIT; }
        else this.patrouille(r);
        break;
      }
      case ETAT.POURSUIT: {
        r.frappe = 1;
        if (this.palet.dy <= 0) { this.etat = ETAT.RECENTRE; break; }
        const f = this.poursuit(r, this.cible);
        if (f) { this.frappeVers = f; this.etat = ETAT.FRAPPE_A; }
        break;
      }
      case ETAT.FRAPPE_A: {
        const avant = { x: r.x, y: r.y };
        this.frappe(r, this.frappeVers);
        // L'etat 6 est atteint « arrive a destination » (PHYSICS.md).
        if ((r.x === avant.x && r.y === avant.y) || this.palet.dy <= 0)
          this.etat = ETAT.RECENTRE;
        break;
      }
      case ETAT.RECENTRE:
        r.frappe = 1;
        this.recentre(r);
        if (this.palet.dy > 0) this.etat = ETAT.ANTICIPE;
        break;
      default:
        this.etat = ETAT.ANTICIPE;
    }
  }
}
