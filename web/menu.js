// menu.js — le menu de la barre d'espace et ses fenetres de reglage.
//
// Transcription de $01299E et de tout ce qu'il appelle :
//
//   - une pile de menus ($1B664, compte $1A51A). Chaque menu est un
//     enregistrement de 12 octets : x, y, liste d'entrees, type, entree
//     choisie. Type 1, la barre du haut ($12EF6 dessin, $1307A choix) ;
//     type 0, une boite deroulante ($12CC6 dessin, $12DCA choix) ;
//   - a chaque tour de boucle, $ED06 redessine tout : le decor seul ($EC94 :
//     la table et le tableau des points, sans personnage ni raquettes), puis
//     les menus de la pile ($11D3A), sauf si une fenetre est ouverte ;
//   - les fenetres a curseurs ($1348C) : un titre, des curseurs de 26 octets
//     (libelle, plancher, plafond, variable, min, max, rappel, sauvegarde),
//     deux boutons SET-IT et CANCEL.
//
// La souris du ST : bit 0 de $1A7A2 = bouton droit, bit 1 = bouton gauche ;
// $1A7B2 / $1A7B4 = position absolue. Un clic droit annule partout.
//
// Les boucles d'attente du ST (« tant que le bouton est enfonce ») sont
// ecrites ici comme des fonctions async : chaque `await this.image()` rend
// la main pour une image, comme l'echange d'ecran $DC14.

import { texte } from './fonte.js';

const LARGEUR_CAR = 6;            // $18170 compte des caracteres ; 6 px chacun

export class Menu {
  constructor(m, moteur, interfaceImg, interfaceJson, palette) {
    this.m = m; this.mo = moteur;
    this.img = interfaceImg; this.json = interfaceJson;
    this.palette = palette;
    this.pile = [];               // $1B664
    this.dialogue = null;         // $1A51C
    this.ouvert = false;
    this.ecranScores = false;
    this.souris = { x: 160, y: 40, gauche: false, droit: false };
    this.attente = null;          // la boucle en cours attend l'image suivante
  }

  // --- les primitives du ST ------------------------------------------------
  // $174C8 : sprite pose par le BAS. Bit 15 du numero : le sprite est
  // retourne horizontalement ($175F0 le retourne en memoire, sur toute sa
  // largeur en mots de 16 px), le x restant le bord gauche. C'est ainsi que
  // sont faits les coins et le bord droits du cadre ($8012, $8013, $8015).
  sprite(g, k, x, bas) {
    const s = this.json.sprites[k & 0x7FFF];
    if (k & 0x8000) {
      g.save();
      g.translate(x + s.w, 0); g.scale(-1, 1);
      g.drawImage(this.img, s.x, s.y, s.w, s.h, 0, bas - s.h + 1, s.w, s.h);
      g.restore();
    } else {
      g.drawImage(this.img, s.x, s.y, s.w, s.h, x, bas - s.h + 1, s.w, s.h);
    }
  }
  // $17E78 : pave plein, bornes comprises.
  pave(g, x1, y1, x2, y2, c) {
    g.fillStyle = this.palette[c];
    g.fillRect(Math.min(x1, x2), Math.min(y1, y2), Math.abs(x2 - x1) + 1, Math.abs(y2 - y1) + 1);
  }
  // $14F4E puis $14FA4 : une chaine, y = ligne du haut.
  texte(g, chaine, x, y, c) { texte(g, this.m.fonte, chaine, x, y, this.palette[c]); }

  // --- $012B32 : le cadre d'une boite -----------------------------------------
  cadre(g, x, y, w, h) {
    for (let a = x + 2; a < x + w - 2; a += 7) {
      this.sprite(g, 0x14, a, y + 2);
      this.sprite(g, 0x16, a, y + h + 5);
    }
    for (let a = y + 2; a < y + h + 5; a += 8) {
      this.sprite(g, 0x15, x - 5, a);
      this.sprite(g, 0x8015, x + w - 10, a);
    }
    this.sprite(g, 0x12, x - 5, y + 2);
    this.sprite(g, 0x13, x - 5, y + h + 5);
    this.sprite(g, 0x8012, x + w - 10, y + 2);
    this.sprite(g, 0x8013, x + w - 10, y + h + 5);
    this.pave(g, x, y, x + w, y + h, 2);
  }

  // --- $012CC6 : une boite deroulante ------------------------------------------
  // Largeur : la plus longue entree * 6 - 1 ; hauteur : 9 par entree - 2.
  // L'entree pointee est ecrite en couleur 15, les autres en 0.
  dimensions(menu) {
    const n = menu.entrees.length;
    const l = Math.max(...menu.entrees.map((e) => e.length));
    return [l * LARGEUR_CAR - 1, n * 9 - 2];
  }
  dessinerBoite(g, menu) {
    const [w, h] = this.dimensions(menu);
    this.cadre(g, menu.x, menu.y, w, h);
    menu.entrees.forEach((e, i) =>
      this.texte(g, e, menu.x + 6, menu.y + 9 * i, i === menu.choix ? 15 : 0));
  }

  // --- $012EF6 : la barre du haut ------------------------------------------------
  // Les entrees se partagent 280 px : l'ecart entre elles est ce qui reste
  // apres leur texte, divise par (n - 1). Sprite 17 pose en (x, y + 32) ;
  // textes en (x + 16 + position, y + 11), l'entree pointee en couleur 2.
  positions(menu) {
    const n = menu.entrees.length;
    const total = menu.entrees.reduce((s, e) => s + e.length, 0);
    const ecart = Math.trunc((280 - total * LARGEUR_CAR) / (n - 1));
    const pos = [0];
    for (const e of menu.entrees) pos.push(pos[pos.length - 1] + e.length * LARGEUR_CAR + ecart);
    return [pos, ecart];
  }
  dessinerBarre(g, menu) {
    const [pos] = this.positions(menu);
    this.sprite(g, 17, menu.x, menu.y + 32);
    menu.entrees.forEach((e, i) =>
      this.texte(g, e, menu.x + 16 + pos[i], menu.y + 11, i === menu.choix ? 2 : 0));
  }

  // --- $011D3A : la pile de menus, sauf si une fenetre est ouverte -----------
  dessinerPile(g) {
    if (this.dialogue) return;
    for (const menu of this.pile) {
      if (menu.type) this.dessinerBarre(g, menu);
      else this.dessinerBoite(g, menu);
    }
  }

  // --- $011DF6 : le choix dans le menu du haut de la pile ----------------------
  // Attendre que les boutons soient relaches, puis suivre la souris : l'entree
  // survolee devient l'entree choisie (et s'eclaire). Clic droit : -1. Clic
  // gauche : on attend qu'il soit relache, et c'est l'entree survolee au
  // moment de l'appui.
  async choisir() {
    const menu = this.pile[this.pile.length - 1];
    while (this.souris.gauche || this.souris.droit) await this.image();
    for (;;) {
      menu.choix = menu.type ? this.survolBarre(menu) : this.survolBoite(menu);
      if (this.souris.droit) { menu.choix = -1; return -1; }
      if (this.souris.gauche) {
        while (this.souris.gauche) await this.image();
        return menu.choix;
      }
      await this.image();
    }
  }
  // $12E5A
  survolBoite(menu) {
    const [w, h] = this.dimensions(menu), { x, y } = this.souris;
    if (x >= menu.x && x < menu.x + w && y >= menu.y && y < menu.y + h)
      return Math.trunc((y - menu.y) / 9);
    return -1;
  }
  // $13154
  survolBarre(menu) {
    const [pos, ecart] = this.positions(menu);
    const rx = this.souris.x - menu.x - 16, ry = this.souris.y - menu.y - 11;
    if (rx < 0 || rx >= 280 || ry < 0 || ry >= 8) return -1;
    let i = 0;
    while (i < menu.entrees.length && rx >= pos[i + 1] - Math.trunc(ecart / 2)) i++;
    return i;
  }

  empiler(def, entrees) {                                       // $11DD2
    const menu = { x: def.x, y: def.y, type: def.type,
                   entrees: entrees || def.entrees, choix: 0 };
    this.pile.push(menu);
    return menu;
  }
  depiler() { this.pile.pop(); }                                // $11E7A

  // --- les variables des curseurs ------------------------------------------------
  // Une adresse de la memoire d'origine, nommee a l'export : « joueur.* »
  // ($19CF4), « dc3.* » ($1B60C), « obstacle.* » ($19CEA), « passage »
  // ($1AFDE, ou le menu depose une taille divisee par 5).
  objet(nom) {
    const [o, cle] = nom.split('.');
    if (o === 'passage') return [this, 'passage'];
    return [{ joueur: this.mo.J, dc3: this.mo.dc3, obstacle: this.mo.O }[o], cle];
  }
  lire(nom) { const [o, k] = this.objet(nom); return o[k]; }
  ecrire(nom, v) { const [o, k] = this.objet(nom); o[k] = v; }

  // --- $013354 puis $013222 : une fenetre ---------------------------------------
  dessinerDialogue(g) {
    const d = this.dialogue;
    const n = d.curseurs.length, bas = n * 30 + 50;
    this.cadre(g, 15, 5, 290, bas);
    this.sprite(g, 0x19, 239, bas + 3);                 // CANCEL
    this.sprite(g, 0x1A, 25, bas + 3);                  // SET-IT
    this.texte(g, d.titre, 160 - d.titre.length * 3, 10, 15);
    d.curseurs.forEach((c, i) =>
      this.texte(g, c.libelle, 160 - c.libelle.length * 3, 25 + 30 * i, 15));
    // $13222 : les curseurs. Le bouton est a (v - min) * 241 / (max - min).
    d.curseurs.forEach((c, i) => {
      const y = 25 + 30 * i;
      this.pave(g, 17, y + 11, 304, y + 28, 2);
      this.sprite(g, 0x17, 17, y + 28);
      const v = this.lire(c.variable);
      const x = Math.trunc((v - c.min) * 241 / (c.max - c.min)) + 21;
      this.sprite(g, 0x18, x, y + 25);
      this.texte(g, String(v), x + 9, y + 16, 0);
    });
  }

  // --- $011E8E puis $01348C : une fenetre, jusqu'a SET-IT (1) ou CANCEL (0) ----
  async regler(adresse) {
    const d = this.m.menu.dialogues[adresse];
    this.dialogue = d;
    const n = d.curseurs.length, bas = n * 30 + 53;
    const sauve = d.curseurs.map((c) => this.lire(c.variable));     // +$18
    const annuler = () => d.curseurs.forEach((c, i) => this.ecrire(c.variable, sauve[i]));
    let r;
    while (this.souris.gauche || this.souris.droit) await this.image();
    let pris = -1;
    for (;;) {
      let dx = this.souris.x - 15;
      const dy = this.souris.y - 5;
      if (this.souris.droit) { annuler(); r = 0; break; }
      if (!this.souris.gauche) pris = -1;
      else {
        if (dy >= bas - 20 && dy < bas && pris === -1) {
          if (dx >= 224 && dx < 280) { annuler(); r = 0; break; }
          if (dx >= 10 && dx < 66) { r = 1; break; }
        } else if (dy >= 20 && dy < bas && pris === -1) {
          dx = Math.min(Math.max(dx, 17), 259);
          const reste = (dy - 20) % 30;
          if (reste >= 17 && reste < 28) pris = Math.trunc((dy - 20) / 30);
        }
        if (pris >= 0) {
          const c = d.curseurs[pris];
          const t = Math.min(Math.max(dx - 17, 0), 241) * (c.max - c.min);
          this.ecrire(c.variable, Math.trunc(t / 241) + c.min);
          // Les liens : un minimum ne depasse pas son maximum, et
          // inversement, pour tous les curseurs de la fenetre.
          for (const k of d.curseurs) {
            if (k.plancher && this.lire(k.variable) < this.lire(k.plancher))
              this.ecrire(k.variable, this.lire(k.plancher));
            if (k.plafond && this.lire(k.variable) > this.lire(k.plafond))
              this.ecrire(k.variable, this.lire(k.plafond));
          }
        }
      }
      await this.image();
    }
    this.dialogue = null;
    return r;
  }

  // =========================================================================
  //  Les menus eux-memes
  // =========================================================================

  // La page quitte la partie alors que le menu est ouvert : la boucle en
  // cours est abandonnee (elle n'aura plus d'image).
  fermer() {
    this.pile = []; this.dialogue = null; this.attente = null;
    this.ouvert = false; this.ecranScores = false;
  }

  // Une image : la boucle en cours reprend a la prochaine image de la page.
  image() { return new Promise((ok) => { this.attente = ok; }); }
  // Appelee par la page a chaque image, apres avoir mis la souris a jour.
  avancer() {
    const a = this.attente;
    this.attente = null;
    if (a) a();
  }

  // --- $01299E : le menu, ouvert par la barre d'espace ($FD38) ------------------
  // Renvoie l'etat du jeu $1B57E : 1 on reprend, 2 nouvelle partie, 3 le bar.
  async ouvrir() {
    const M = this.m.menu, mo = this.mo;
    this.ouvert = true;
    this.souris.y = 40;                                 // $DB2C
    this.etat = 1;
    // Hors tournoi : scores, jeu, palette, obstacle, et « robot » contre
    // Dc3 seulement ($1B5AC = 8).
    const entrees = M.barre.entrees.slice(0, 4);
    if (mo.idx === 8) entrees.push(M.barre.entrees[4]);
    this.empiler(M.barre, entrees);
    let fini = false;
    while (!fini && this.etat === 1) {
      switch (await this.choisir()) {
        case -1: fini = true; break;
        case 0: await this.scores(); break;
        case 1: await this.jeu(); break;
        case 2: await this.palette(); break;
        case 3: await this.obstacle(); break;
        case 4: await this.robot(); break;
      }
    }
    this.depiler();
    while (this.souris.gauche || this.souris.droit) await this.image();
    this.ouvert = false;
    return this.etat;
  }

  // --- $012684 : le tableau des maitres -------------------------------------------
  async scores() {
    this.ecranScores = true;
    while (this.souris.gauche || this.souris.droit) await this.image();
    while (!this.souris.gauche && !this.souris.droit) await this.image();
    this.ecranScores = false;
  }
  // Les noms en colonnes de 15, a x = 30 puis 180, y = 63 + 8 par ligne ; le
  // score « 15-n » a 85 px du nom. On s'arrete au premier nom vide.
  dessinerScores(g, fond) {
    g.drawImage(fond, 0, 0);
    const t = this.m.menu.tableau;
    for (let i = 0; i < 30 && t[i][0]; i++) {
      const x = i < 15 ? 30 : 180, y = (i % 15) * 8 + 63;
      this.texte(g, t[i][0], x, y, 15);
      this.texte(g, '15-' + t[i][1], x + 85, y, 15);
    }
  }

  // --- $012246 : jeu ---------------------------------------------------------------
  async jeu() {
    this.empiler(this.m.menu.jeu);
    for (;;) {
      const r = await this.choisir();
      if (r === -1) { this.depiler(); return; }
      if (r === 0) { this.depiler(); this.etat = 2; return; }     // nouvelle partie
      if (r === 1) { this.depiler(); this.etat = 3; return; }     // nouvel adversaire
      // r === 2, charge tournoi ($13B20). Le fichier tourname.dat n'existe
      // pas ici ; quand $13B20 echoue, $122DA enchaine sur « nouvel
      // adversaire » : retour au bar.
      if (r === 2) { this.depiler(); this.etat = 3; return; }
    }
  }

  // --- $012370 : palette (celle du joueur) ---------------------------------------
  async palette() {
    const mo = this.mo;
    this.empiler(this.m.menu.palette);
    for (;;) {
      const r = await this.choisir();
      if (r === -1) { this.depiler(); return; }
      if (r === 0) {
        this.passage = Math.trunc(mo.J.largeur / 5);
        if (await this.regler('1A40A')) { mo.J.largeur = this.passage * 5; mo.J.x = 0; }
      } else if (r === 1) await this.regler('1A414');
      else if (r === 2) await this.regler('1A41E');
      else if (r === 3) {                                 // palette de tournoi
        Object.assign(mo.J, this.m.joueur_tournoi);
        this.depiler(); return;
      }
    }
  }

  // --- $012434 : obstacle -----------------------------------------------------------
  async obstacle() {
    const O = this.mo.O;
    this.empiler(this.m.menu.obstacle);
    const r = await this.choisir();
    if (r === 0) O.actif = 0;
    else if (r >= 1 && r <= 3) Object.assign(O, this.m.obstacle.tout_faits[r - 1]);
    else if (r === 4) {                                   // definir un obstacle
      this.passage = Math.trunc(O.taille / 5);
      if (await this.regler('1A428')) {
        O.taille = this.passage * 5; O.actif = 1; O.x = 0; O.vx = 0;
      }
    }
    this.depiler();
  }

  // --- $012510 : robot, la copie de travail de Dc3 --------------------------------
  // Apres chaque SET-IT, le code recopie certains reglages sur leurs jumeaux.
  async robot() {
    const D = this.mo.dc3;
    this.empiler(this.m.menu.robot);
    for (;;) {
      const r = await this.choisir();
      if (r === -1) { this.depiler(); return; }
      if (r === 0) {                                                  // taille palette
        this.passage = Math.trunc(D.largeur / 5);
        if (await this.regler('1A432')) { D.largeur = this.passage * 5; D.x = 0; }
      } else if (r === 1) {                                           // puissance palette
        if (await this.regler('1A43C')) { D.reflex_x2 = D.reflex_x; D.reflex_y2 = D.reflex_y; }
      } else if (r === 2) {                                           // attente
        this.passage = 150 - D.y_pres;
        if (await this.regler('1A446')) {
          D.x_min = -D.x_max;
          D.y_pres = 150 - this.passage;
          D.y_loin = this.passage + 150;
          D.vr_droite = D.v_attente_x;
          D.vr_pres = D.v_attente_y;
        }
      } else if (r === 3) {                                           // vitesse palette
        if (await this.regler('1A450')) {
          D.pas_gauche = D.v_attaque; D.pas_arriere = D.v_attaque; D.pas_avant = D.v_attaque;
          // $1262E recopie $1B644 sur lui-meme : le pas de frappe en Y ne
          // suit PAS la vitesse de defense. Sans doute une coquille, gardee.
        }
      } else if (r === 4) await this.regler('1A45A');                // puissance frappe
      else if (r === 5) await this.regler('1A464');                  // puissance service
    }
  }

  // --- le dessin d'une image de menu ($ED06) -----------------------------------
  dessiner(g, decor) {
    if (this.ecranScores) { this.dessinerScores(g, decor.scores); return; }
    decor.dessiner(g);
    if (this.dialogue) this.dessinerDialogue(g);
    else this.dessinerPile(g);
  }
}
