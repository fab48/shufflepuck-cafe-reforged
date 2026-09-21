// moteur.js — la boucle de jeu de Shufflepuck Cafe, transcrite du 68000.
//
// Deuxieme version. La premiere transcrivait les routines isolees mais
// INVENTAIT tout ce qui les reliait : la detection de collision, les
// transitions de l'IA, le bornage de la raquette adverse, le service, le
// point. Tout cela a depuis ete lu dans le code, et c'est ce qui est ici.
//
// Chaque fonction porte l'adresse de la routine d'origine. Les variables
// portent le nom de leur adresse memoire quand elles sont globales dans
// l'original : c'est plus laid, mais on peut tout verifier au desassembleur.
//
// Arithmetique : tout est en mots de 16 bits signes, et le 68000 divise en
// tronquant VERS ZERO (DIVS). `div()` et `w16()` reproduisent l'un et l'autre.
//
// Ce qui reste une reconstruction est signale par RECONSTRUCTION.

export const ETAT_JEU = Object.freeze({   // $1B594, repartiteur 0x0105F0
  RETOUR_JOUEUR: 1,     // le palet revient au point de service du joueur
  RETOUR_ADV: 2,        // ... de l'adversaire
  JEU: 3,               // la partie
  FIN: 4,               // quelqu'un a 15 points
  POINT: 5,             // la vitre se brise
  LANCER_BEJIN: 6,      // le palet part tout seul (service de Bejin)
});

export const ETAT_ADV = Object.freeze({   // $1B598, repartiteur 0x010F3A
  ANTICIPE: 0, POURSUIT: 1, FRAPPE: 2, SERVICE: 3,
  IMMOBILE_4: 4, IMMOBILE_5: 5, RECENTRE: 6, FRAPPE_SERVICE: 7,
});

// Index dans la table $19D14 (et donc $1B5AC).
const LEXAN = 3, NERUAL = 4, ENEG = 5, BEJIN = 6, BIFF = 7, DC3 = 8;

/** Division tronquee vers zero, comme DIVS. */
export const div = (a, b) => Math.trunc(a / b);
/** Ramene a un mot signe de 16 bits, comme toute operation .w */
export const w16 = (v) => ((v + 32768) & 0xFFFF) - 32768;

/** $00FDEC */
export function borner(min, v, max) {
  if (v < min) return min;
  if (v > max) return max;
  return v;
}

export class Moteur {
  constructor(m) {
    this.k = m.moteur;
    this.m = m;
    this.graine = 12345;                 // $1AFB4
    this.sons = [];                      // sons declenches pendant l'image
    this.nouvellePartie(0);
  }

  // --- $00FD94 : le generateur aleatoire d'origine --------------------------
  // Une congruence lineaire avec un terme supplementaire (graine >> 20).
  rand() {
    const g = this.graine >>> 0;
    const p = Number((BigInt(g) * 0x41C64E6Dn) & 0xFFFFFFFFn);
    this.graine = (p + (g >>> 20) + 0x3039) >>> 0;
    return (this.graine >>> 16) & 0x7FFF;
  }

  // --- $00FDCE : tirage dans [min, max] --------------------------------------
  // Reste d'une DIVS, dont le signe suit le dividende (toujours positif ici).
  // Si max < min, le diviseur est negatif et le tirage tombe dans
  // [min, min + |diviseur| - 1] : c'est ce qui arrive a Skip avec (34, 30).
  alea(min, max) {
    const n = max - min + 1;
    const r = this.rand();
    if (n === 0) return min;             // le 68000 leverait une exception
    return w16(min + (r % Math.abs(n)));
  }

  // --- $00FE9E : a * b / c, en 16 bits ---------------------------------------
  muldiv(a, b, c) { return w16(div(a * b, c)); }

  nouvellePartie(index) {
    const m = this.m;
    // La table des neuf blocs. Les blocs statiques sont partages : quand
    // Nerual copie la frappe du joueur, il modifie SON bloc, durablement.
    this.table = m.table_adversaires.map((b) => Object.assign({}, b,
      { x: 0, y: 1500, vx: 0, vy: 0, frappe: 1 }));
    this.lexanSobre = Object.assign({}, this.table[LEXAN]);
    const g = m.joueur;
    this.J = {                          // $19CF4, bloc court du joueur
      x: 0, y: g.y, vx: 0, vy: 0, largeur: g.largeur, frappe: 0,
      reflex_x: g.reflex_x, reflex_y: g.reflex_y, accel_x: g.accel_x, accel_y: g.accel_y,
      reflex_x2: g.reflex_x2, reflex_y2: g.reflex_y2, accel_x2: g.accel_x2, accel_y2: g.accel_y2,
    };
    this.D = 100;                       // $19CE8, le diviseur des coefficients
    this.P = { x: 0, y: 0, dx: 0, dy: 0 };   // $1B58C..$1B592
    this.s0 = 0; this.s1 = 0;           // $1B588 (adversaire), $1B58A (joueur)
    this.serveur = 1;                   // $1B584  RECONSTRUCTION : valeur initiale
    this.fin = 0;                       // $1B586
    this.nerualCopie = 0;               // $1B59A
    this.bejinB2 = 0; this.bejinB4 = 0; // $1B5B2, $1B5B4
    this.compteService = 30;            // $19D12
    // Les globales de l'IA ($1AFB8..$1AFCE)
    this.vpx = 0; this.vpy = 0;
    this.sim = { x: 0, y: 0, dx: 0, dy: 0 };
    this.cibleX = 0; this.cibleY = 0;
    this.xAv = 0; this.yAv = 0; this.xN = 0; this.yN = 0;
    this.vitre = null;
    this.choisirAdversaire(index);
    this.paletAuService();              // $FEB0
    this.etatJeu = this.serveur ? ETAT_JEU.RETOUR_JOUEUR : ETAT_JEU.RETOUR_ADV;
    this.etatAdv = ETAT_ADV.RECENTRE;
  }

  // --- $0106DC : choix de l'adversaire ----------------------------------------
  // Seul Lexan joue sur une copie de travail, restauree a 0-0 : c'est ce qui
  // permet a l'ivresse de s'accumuler au fil d'une partie sans abimer la
  // table.
  choisirAdversaire(index) {
    this.idx = index;
    if (index === LEXAN && this.s0 === 0) {
      this.table[LEXAN] = Object.assign({}, this.lexanSobre,
        { x: 0, y: 1500, vx: 0, vy: 0, frappe: 1 });
    }
    this.A = this.table[index];
    this.A.x = 0; this.A.y = 1350;
    this.A.raquetteVisible = 1;               // +$1C, pose par $0106DC
    this.evenements = [];
    this.ivresses = 0;
  }

  // --- $00FEB0 : le palet au point de service ---------------------------------
  paletAuService() {
    const P = this.P;
    P.x = 0;
    P.y = this.serveur ? 295 : 1205;
    P.dx = 0; P.dy = 0;
    this.etatJeu = ETAT_JEU.JEU;
  }

  son(banque, sequence) { this.sons.push({ banque, sequence }); }

  // =========================================================================
  //  UNE IMAGE — l'ordre est celui de la boucle 0x00DAA4
  // =========================================================================
  image(sourisDx, sourisDy, bouton) {
    this.sons = [];
    this.evenements = [];                      // pour les animations
    this.joueur(sourisDx, sourisDy, bouton);   // $FD38 -> $FB7A
    this.ia();                                 // $10EAA
    this.palet();                              // $1034C
    this.vitreAnime();                         // $F288 / $F336
    this.score();                              // $D4D4
  }

  // --- $00FB7A : la raquette du joueur ----------------------------------------
  joueur(sx, sy, bouton) {
    const J = this.J;
    let dx = borner(-32, sx, 32);
    let dy = borner(-32, sy, 32);
    // Courbe d'acceleration : |d|/2 d'abord, puis * d, puis / 4.
    dx = w16(dx + div(dx * (Math.abs(dx) >> 1), 4));
    dy = w16(dy + div(dy * (Math.abs(dy) >> 1), 4));
    dx = borner(-200, dx, 200);
    dy = borner(-200, dy, 200);
    const demi = J.largeur >> 1;
    const nx = borner(demi - 250, J.x + dx, 250 - demi);
    J.vx = nx - J.x; J.x = nx;
    // La raquette du joueur vit dans [0, 300]. Y est inverse.
    const ny = borner(0, J.y - dy, 300);
    J.vy = ny - J.y; J.y = ny;
    // Bouton enfonce : second jeu de coefficients (accel_y 140 au lieu de 130).
    J.frappe = bouton ? 1 : 0;
  }

  // =========================================================================
  //  LE PALET — repartiteur 0x0105F0 sur $1B594
  // =========================================================================
  palet() {
    const P = this.P;
    switch (this.etatJeu) {
      case ETAT_JEU.RETOUR_JOUEUR:                      // $10368
        P.x += borner(-15, -P.x, 15);
        P.y += borner(-60, 295 - P.y, 60);
        if (P.x === 0 && P.y === 295) {
          this.paletAuService();
          this.etatAdv = ETAT_ADV.RECENTRE;
        }
        break;
      case ETAT_JEU.RETOUR_ADV:                         // $103D6
        P.x += borner(-15, -P.x, 15);
        P.y += borner(-60, 1205 - P.y, 60);
        if (P.x === 0 && P.y === 1205) {
          this.paletAuService();
          if (this.idx === DC3) {               // $010438 : Dc3 prend la pose
            this.evenements.push({ ecrire: [0x199D4, 6] });
            this.evenements.push({ lancer: 0x199B6, mode: 0 });
          }
          this.etatAdv = ETAT_ADV.SERVICE;
        }
        break;
      case ETAT_JEU.JEU:
        this.paletAvance();
        break;
      case ETAT_JEU.LANCER_BEJIN:
        this.lancerBejin();
        break;
      default:                                          // 0, 4, 5
        this.etatAdv = ETAT_ADV.RECENTRE;
    }
  }

  // --- $010466 : la partie proprement dite -----------------------------------
  paletAvance() {
    const P = this.P;
    P.dx = borner(-150, P.dx, 150);
    P.dy = borner(-300, P.dy, 300);
    P.x = w16(P.x + P.dx);
    P.y = w16(P.y + P.dy);
    if (P.x < -226) {
      this.son(1, this.sequenceRebond(P.y));
      P.dx = -P.dx; P.x = -452 - P.x;
    }
    if (P.x > 226) {
      this.son(1, this.sequenceRebond(P.y));
      P.dx = -P.dx; P.x = 452 - P.x;
    }
    this.collisionJoueur();     // $10096
    this.collisionAdversaire(); // $101D0
    // $1023C : l'obstacle, desactive ($19CF2 = 0) — non transcrit
    // Le palet ne SORT jamais : il est borne, et c'est $D4D4 qui constate
    // qu'il touche un fond.
    P.y = borner(-18, P.y, 1500);
  }

  // $11486 : la sequence de rebond, selon la profondeur.
  sequenceRebond(y) { return borner(4, div(y, 68) + 4, 25); }

  // --- $00FEEC : collision --------------------------------------------------
  // Renvoie 1 s'il y a contact. Le test en X est BALAYE : l'intervalle
  // parcouru par le palet pendant l'image, relativement a la raquette,
  // elargi de 24 (le rayon du palet), doit chevaucher la raquette.
  collision(r) {
    const P = this.P;
    const rel = w16(P.dx - r.vx);
    let a, b;
    if (rel > 0) { a = 0; b = rel; } else { a = rel; b = 0; }
    const demi = r.largeur >> 1;
    if (!(P.x - a + 24 > r.x - demi)) return 0;
    if (!(P.x - b - 24 < r.x + demi)) return 0;

    // $1151C : le son de frappe, plus grave dans la moitie lointaine.
    this.son(1, P.y > 750 ? 1 : 0);

    // Chaque terme est divise SEPAREMENT par $19CE8 (100), puis additionne.
    const md = (x, y) => this.muldiv(x, y, this.D);
    if (!r.frappe) {
      P.dx = w16(md(P.dx, r.reflex_x) + md(r.vx, r.accel_x));
      P.dy = w16(md(r.vy, r.accel_y) - md(P.dy, r.reflex_y));
    } else {
      P.dx = w16(md(P.dx, r.reflex_x2) + md(r.vx, r.accel_x2));
      P.dy = w16(md(r.vy, r.accel_y2) - md(P.dy, r.reflex_y2));
    }
    return 1;
  }

  // --- $010096 : contact avec la raquette du joueur -----------------------
  // On compare les positions de l'image PRECEDENTE (position - vitesse) :
  // de quel cote du palet se trouvait la raquette ? Puis on teste le
  // franchissement avec une marge de 24.
  collisionJoueur() {
    const P = this.P, J = this.J;
    const cote = (P.y - P.dy) > (J.y - J.vy) ? 1 : 0;
    let touche;
    if (cote) touche = P.y - 24 < J.y;
    else touche = P.y + 24 > J.y;
    if (!touche) return;
    if (!this.collision(J)) return;

    P.y = cote ? J.y + 24 : J.y - 24;             // le palet est repose contre la raquette
    if (P.y > 300 && P.dy < 5) P.dy = 5;          // vitesse de fuite minimale

    // Nerual : a la premiere frappe du joueur apres certains points, il
    // RECOPIE ce coup dans son propre bloc (acceleration, et vecteur de
    // service). C'est sa facon de "copier" le joueur.
    if (this.nerualCopie) {
      this.nerualCopie = 0;
      const N = this.table[NERUAL];
      if (!J.frappe) { N.accel_x = J.accel_x; N.accel_y = J.accel_y; }
      else { N.accel_x = J.accel_x2; N.accel_y = J.accel_y2; }
      const vy = J.vy < 5 ? 5 : J.vy;
      N.cible_y_min = vy; N.cible_y_max = vy;
      N.cible_x_min = J.vx; N.cible_x_max = J.vx;
    }
  }

  // --- $0101D0 : contact avec la raquette adverse --------------------------
  // Asymetrique : pas de marge de 24 ici. La raquette doit etre passee du
  // cote lointain du palet a son niveau ou en deca.
  collisionAdversaire() {
    const P = this.P, A = this.A;
    if (!((A.y - A.vy) > (P.y - P.dy))) return;
    if (!(A.y <= P.y)) return;
    if (!this.collision(A)) return;
    P.y = A.y - 3;
    if (P.dy > -5) P.dy = -5;
  }

  // --- $01054A : le palet lance par Bejin -----------------------------------
  lancerBejin() {
    const P = this.P;
    if (P.y > 750) { P.y -= 50; return; }
    if (P.x > -100 && P.x < 100) { P.x += this.bejinB2 ? 10 : -10; return; }
    P.dy = this.alea(-200, -150);
    if (this.bejinB4) P.dx = w16(div(w16(P.dy * 7), 16));
    else P.dx = div(-P.dy, 5);
    if (P.x < 0) P.dx = -P.dx;
    this.etatJeu = ETAT_JEU.JEU;
  }

  // =========================================================================
  //  L'IA — repartiteur 0x010EAA
  // =========================================================================
  ia() {
    const A = this.A;
    this.xAv = A.x; this.yAv = A.y;          // $1AFC8, $1AFCA
    switch (this.etatAdv) {
      case 0: this.anticipe();       A.frappe = 1; break;
      case 1: this.poursuit();       A.frappe = 1; break;
      case 2: this.frappe();         A.frappe = 0; break;
      case 3: this.service();        A.frappe = 1; break;
      case 6: this.recentre();       A.frappe = 1; break;
      case 7: this.frappeService();  A.frappe = 0; break;
      default: break;                // 4, 5 : immobile
    }
    // $10F68 : le tremblement, sauf en recentrage et a l'arret.
    if ([0, 1, 2, 3, 7].includes(this.etatAdv) && A.tremblement) {
      if (this.xN !== this.xAv) this.xN = w16(this.xN + this.alea(-A.tremblement, A.tremblement));
      if (this.yN !== this.yAv) this.yN = w16(this.yN + this.alea(-A.tremblement, A.tremblement));
    }
    // $11000 : la seule borne de la raquette adverse.
    const demi = A.largeur >> 1;
    this.xN = borner(demi - 250, this.xN, 250 - demi);
    this.yN = borner(1200, this.yN, 1500);
    A.x = this.xN; A.y = this.yN;
    // La vitesse est le deplacement reel. C'est ce qui fait la frappe.
    A.vx = w16(this.xN - this.xAv);
    A.vy = w16(this.yN - this.yAv);
    if (this.P.dy < 0 && this.etatAdv !== 0) this.etatAdv = ETAT_ADV.RECENTRE;
  }

  // --- $010802 : patrouille -------------------------------------------------
  // La vitesse de patrouille est GLOBALE ($1AFB8, $1AFBA), pas dans le bloc.
  patrouille() {
    const A = this.A;
    const demi = div(A.largeur, 2);
    this.xN = w16(this.xAv + this.vpx);
    this.yN = w16(this.yAv + this.vpy);
    if ((this.xN >= A.x_max || this.xN + demi >= 250) && this.vpx >= 0) {
      this.xN = A.x_max; this.vpx = -A.vr_droite;
    } else if ((this.xN <= A.x_min || this.xN - demi <= -250) && this.vpx <= 0) {
      this.xN = A.x_min; this.vpx = A.v_attente_x;
    }
    if (this.yN >= 1500 - A.y_pres && this.vpy >= 0) {
      this.yN = 1500 - A.y_pres; this.vpy = -A.vr_pres;
    } else if (this.yN <= 1500 - A.y_loin && this.vpy <= 0) {
      this.yN = 1500 - A.y_loin; this.vpy = A.v_attente_y;
    }
  }

  // --- $01096C : recentrage, puis retour a l'anticipation ------------------
  recentre() {
    const A = this.A;
    this.vpx = this.xAv > div(A.x_min + A.x_max, 2) ? -A.vr_droite : A.v_attente_x;
    this.vpy = (1500 - this.yAv) > div(A.y_pres + A.y_loin, 2) ? A.v_attente_y : -A.vr_pres;
    this.patrouille();
    this.etatAdv = ETAT_ADV.ANTICIPE;
  }

  // --- $010730 : borne le point simule dans la zone adverse ---------------
  bornerSim() {
    const demi = this.A.largeur >> 1;
    this.sim.x = borner(demi - 250, this.sim.x, 250 - demi);
    this.sim.y = borner(1200, this.sim.y, 1500);
  }

  // --- $01078E : un pas de simulation ---------------------------------------
  // S'arrete des que le palet simule entre dans la zone adverse.
  simPas() {
    const s = this.sim;
    if (s.y > 1200) { this.bornerSim(); return 0; }
    s.x = w16(s.x + s.dx); s.y = w16(s.y + s.dy);
    if (s.x < -226) { s.dx = -s.dx; s.x = -452 - s.x; }
    if (s.x > 226) { s.dx = -s.dx; s.x = 452 - s.x; }
    return 1;
  }

  // --- $010A02 : anticipation -------------------------------------------------
  anticipe() {
    const A = this.A, P = this.P;
    this.patrouille();
    if (!(P.dy > 0)) return;
    if (!(P.y > 1500 - A.seuil_reaction)) return;
    if (this.etatJeu !== ETAT_JEU.JEU) return;
    this.etatAdv = ETAT_ADV.POURSUIT;
    this.sim = { x: P.x, y: P.y, dx: P.dx, dy: P.dy };
    this.sim.x = w16(this.sim.x + this.alea(-A.erreur_visee, A.erreur_visee));
    for (let n = A.pas_simulation; n > 0; n--) if (!this.simPas()) break;
  }

  // --- $010AB6 : poursuite ----------------------------------------------------
  // La simulation continue d'avancer d'un pas par image : la cible suit.
  poursuit() {
    const A = this.A;
    this.xN = w16(this.xAv + borner(-A.pas_gauche, this.sim.x - this.xAv, A.v_attaque));
    this.yN = w16(this.yAv + borner(-A.pas_avant, this.sim.y - this.yAv, A.pas_arriere));
    if (this.xAv === this.xN && this.yAv === this.yN) {
      // Arrivee. La cible est retenue, et le point simule devient le point
      // d'ARMEMENT : decale de la dispersion, qui est donc le vecteur de frappe.
      this.etatAdv = ETAT_ADV.FRAPPE;
      this.cibleX = this.sim.x; this.cibleY = this.sim.y;
      this.sim.x = w16(this.sim.x + this.alea(A.disp_x_min, A.disp_x_max));
      this.sim.y = w16(this.sim.y + this.alea(A.disp_y_min, A.disp_y_max));
      this.bornerSim();
      this.xN = this.xAv; this.yN = this.yAv;
    } else {
      this.simPas();
    }
  }

  // --- $010BCE : frappe -------------------------------------------------------
  // La raquette recule vers le point d'armement ; quand le palet va atteindre
  // la cible, elle SAUTE sur la cible en une image. Sa vitesse, egale a son
  // deplacement, devient enorme : c'est cela qui transmet la puissance.
  frappe() {
    const A = this.A, P = this.P;
    if (P.y + P.dy >= this.cibleY) {
      this.xN = this.cibleX; this.yN = this.cibleY;
      this.etatAdv = ETAT_ADV.RECENTRE;
      return;
    }
    this.xN = w16(this.xAv + borner(-A.v_defense, this.sim.x - this.xAv, A.v_defense));
    this.yN = w16(this.yAv + borner(-A.pas_frappe_y, this.sim.y - this.yAv, A.pas_frappe_y));
  }

  // --- $010D44 : service de l'adversaire -------------------------------------
  service() {
    const A = this.A;
    this.patrouille();
    if (--this.compteService !== 0) return;
    this.compteService = 30;
    if (this.idx === BEJIN) {
      // L'indice sonore : le son joue depend du bit qui decide la direction.
      this.bejinB2 = this.rand() & 1;
      this.bejinB4 = this.rand() & 1;
      this.etatAdv = ETAT_ADV.RECENTRE;
      this.son(2, this.bejinB4);
      // Son animation de service ($195BE, mode 0) appelle $F152 a sa derniere
      // image, et c'est cela qui passe le jeu a l'etat 6.
      this.evenements.push({ lancer: 0x195BE, mode: 0 });
      return;
    }
    this.etatAdv = ETAT_ADV.FRAPPE_SERVICE;
    this.cibleX = 0; this.cibleY = 1205;
    if (this.idx === BIFF) {
      // Biff s'adapte au score : plus le joueur mene, plus il sert fort.
      const k = borner(-10, this.s1 - this.s0, 10) + 10;
      this.sim.x = w16(div(w16(A.cible_x_max * k), 20));
      if (this.rand() & 1) this.sim.x = -this.sim.x;
      this.sim.y = w16(div(w16((A.cible_y_max - A.cible_y_min) * k), 20) + A.cible_y_min + 1205);
    } else {
      this.sim.x = this.alea(A.cible_x_min, A.cible_x_max);
      this.sim.y = w16(this.alea(A.cible_y_min, A.cible_y_max) + 1205);
    }
    this.bornerSim();
  }

  // --- $010C7C : frappe de service -------------------------------------------
  frappeService() {
    const A = this.A;
    if (this.sim.x === this.xAv && this.sim.y === this.yAv) {
      this.xN = this.cibleX; this.yN = this.cibleY;
      if (this.idx === DC3) this.evenements.push({ ecrire: [0x199D4, 4] });
      this.etatAdv = ETAT_ADV.RECENTRE;
      return;
    }
    this.xN = w16(this.xAv + borner(-A.v_defense, this.sim.x - this.xAv, A.v_defense));
    this.yN = w16(this.yAv + borner(-A.pas_frappe_y, this.sim.y - this.yAv, A.pas_frappe_y));
  }

  // =========================================================================
  //  LE POINT — $00D4D4
  // =========================================================================
  score() {
    if (this.etatJeu !== ETAT_JEU.JEU) return;
    const P = this.P;
    if (P.y <= 0) this.pointAdversaire();
    else if (P.y >= 1500) this.pointJoueur();
    else return;
    this.serveur = this.serveur ? 0 : 1;       // le service alterne
    this.etatJeu = ETAT_JEU.POINT;
    this.etatAdv = ETAT_ADV.RECENTRE;
    if (this.serveur) this.nerualCopie = 1;
  }

  // $00D3F4 : le palet est passe derriere le joueur. Sa vitre se brise.
  // La reaction du personnage ($F998) suit le meme tirage que l'ivresse.
  pointAdversaire() {
    this.s0++;
    if (this.s0 === 15) { this.evenements.push({ reaction: 4 }); this.fin = 1; }
    else if (this.s0 === 1 || (this.rand() & 1)) {
      this.evenements.push({ reaction: 3 });
      this.lexanBoit();                                        // $110BA
    } else this.evenements.push({ reaction: 0 });
    this.briserVitre(true);
  }

  // $00D468 : le palet est passe derriere l'adversaire.
  pointJoueur() {
    this.s1++;
    if (this.s1 === 15) { this.evenements.push({ reaction: 1 }); this.fin = 2; }
    else if (this.s1 === 1 || (this.rand() & 1)) this.evenements.push({ reaction: 2 });
    else this.evenements.push({ reaction: 0 });
    this.briserVitre(false);
  }

  // --- $0110BA : l'ivresse de Lexan ------------------------------------------
  lexanBoit() {
    if (this.idx !== LEXAN) return;
    const r = this.A;
    const d = (v, num) => { const p = v * num; return p >= 0 ? div(p, 100) : -div(-p, 100); };
    for (const c of ['reflex_x', 'reflex_y', 'accel_x', 'accel_y', 'reflex_x2', 'reflex_y2',
                     'vr_droite', 'v_attente_x', 'v_attente_y', 'vr_pres',
                     'pas_gauche', 'v_attaque', 'pas_arriere', 'pas_avant',
                     'v_defense', 'pas_frappe_y']) r[c] = d(r[c], 82);
    r.x_min = d(r.x_min, 107); r.x_max = d(r.x_max, 107);
    r.erreur_visee = d(r.erreur_visee, 105);
    this.ivresses++;
  }

  // =========================================================================
  //  LA VITRE — $00F23A (depart), $00F288 (pres), $00F336 (loin)
  // =========================================================================
  // Les eclats suivent toujours la meme trajectoire. C'est l'ECHELLE du dessin
  // qui depend de la vitesse du palet a l'impact : plus le tir est violent,
  // plus la vitre vole en grands morceaux.
  briserVitre(pres) {
    const P = this.P;
    // $11586 : fracas en deux temps au-dela de 150, choc sourd en deca.
    this.son(1, (P.dy > 150 || P.dy < -150) ? 2 : 3);
    const echelle = pres ? div(150 - P.dy, 4) : div(P.dy + 150, 8);
    this.vitre = {
      pres, echelle,
      cx: this.projeterX(P.x, P.y),
      cy: pres ? 200 : 67,
      eclats: this.m.vitre.eclats.map((e) => ({ ox: 0, oy: 0, vx: e.vx, vy: e.vy0, lignes: e.lignes })),
    };
  }

  vitreAnime() {
    if (this.etatJeu !== ETAT_JEU.POINT || !this.vitre) return;
    let vivant = 0;
    for (const e of this.vitre.eclats) {
      e.ox = w16(e.ox + (e.vx >> 3));
      e.oy = w16(e.oy + (e.vy >> 3));
      e.vy += 12;                           // gravite
      if (e.oy < 150) vivant = 1;
    }
    if (vivant) return;
    // $00F3FE : fin de l'animation.
    this.vitre = null;
    if (this.s0 === 15 || this.s1 === 15) this.etatJeu = ETAT_JEU.FIN;
    else this.etatJeu = this.serveur ? ETAT_JEU.RETOUR_JOUEUR : ETAT_JEU.RETOUR_ADV;
  }

  // =========================================================================
  //  PROJECTION
  // =========================================================================
  // $DB9C. Centre confirme sur l'image du terrain, a chaque ligne.
  projeterX(x, y) { return div(x * 411, y + 643) + 160; }

  // $DBC2. Le premier argument est une HAUTEUR (site d'appel 0x00DC58).
  projeterY(hauteur, profondeur) {
    const t = div(profondeur * 207, profondeur + 970);
    return (193 - t) - ((hauteur * (164 - t)) >> 9);
  }
}
