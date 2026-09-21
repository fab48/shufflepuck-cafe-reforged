// animation.js — les personnages : scripts d'animation et placement.
//
// Transcription de :
//   $00F480  lancer un script (mode 0 derriere, 1 fond en boucle, 2 devant)
//   $00F440  entrer dans une image : duree * 2/3, fonction de rappel
//   $00F778  dessiner l'image courante, puis avancer
//   $00F690  placer et dessiner un sprite du personnage
//   $00D5B0  composer le decor : bande noire, corps, montants de la table
//   $00F860  l'ordre d'affichage de la scene
//
// Les scripts vivent dans la memoire du programme et SE REECRIVENT : les
// fonctions de rappel du personnage ecrivent le numero de sprite ou la
// duree d'une image directement dans ses octets. On les garde donc sous
// forme de memoire adressable ($18800-$19D00), exportee telle quelle.
//
// Une image de script fait 10 octets :
//   +0 mot   sprite A  (-1 aucun, -2 appeler la fonction tant qu'elle
//                       repond 1, -3 fin : boucle ou disparition)
//   +2 mot   duree
//   +4 long  fonction appelee en entrant dans l'image (0 = aucune)
//   +8 mot   sprite B  (-1 aucun)

export class Memoire {
  constructor(m) {
    this.debut = m.memoire_scripts.debut;
    const bin = atob(m.memoire_scripts.octets);
    this.o = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) this.o[i] = bin.charCodeAt(i);
    this.initial = this.o.slice();
  }
  reinitialiser() { this.o.set(this.initial); }
  w(a) { const i = a - this.debut; const v = (this.o[i] << 8) | this.o[i + 1]; return v >= 0x8000 ? v - 0x10000 : v; }
  l(a) { const i = a - this.debut; return ((this.o[i] << 24) | (this.o[i + 1] << 16) | (this.o[i + 2] << 8) | this.o[i + 3]) >>> 0; }
  ecrire(a, v) { const i = a - this.debut; v &= 0xFFFF; this.o[i] = v >> 8; this.o[i + 1] = v & 0xFF; }
}

// Table de placement de chaque personnage, telle que 0x00D786 la choisit.
// Attention : sa table de saut envoie l'index 4 sur « general » ($1926E) et
// l'index 5 sur « nerual » ($19514), pas dans l'ordre du listing.
const TABLES = [0x188A8, 0x18A42, 0x18CA8, 0x18FC2, 0x1926E, 0x19514, 0x19708, 0x198C4, 0x199FC];

export class Animations {
  constructor(m, moteur) {
    this.m = m;
    this.moteur = moteur;
    this.mem = new Memoire(m);
    this.fond = [];      // $1AF6E
    this.av = [];        // $1AF28
    this.rappels = this.definirRappels();
  }

  // En debut de partie : $00F522 lance les scripts du personnage.
  demarrer(idx) {
    this.mem.reinitialiser();
    this.fond = []; this.av = [];
    this.idx = idx;
    this.table = TABLES[idx];
    for (const s of this.m.adversaires[idx].scripts) this.lancer(s.adresse, s.mode);
  }

  // $00F480
  lancer(script, mode) {
    const slot = { cur: 0, start: 0, compte: 0, boucle: 0, devant: 0 };
    if (mode === 1) { this.fond.push(slot); slot.boucle = 1; }
    else { this.av.push(slot); slot.devant = mode === 2 ? 1 : 0; }
    this.entrer(slot, script);
    slot.start = script;
  }

  // $00F440
  entrer(slot, image) {
    slot.cur = image;
    slot.compte = Math.trunc(this.mem.w(image + 2) * 2 / 3);
    const f = this.mem.l(image + 4);
    if (f) this.appeler(f, slot);
  }

  appeler(f, slot) {
    const r = this.rappels[f];
    if (r) return r(slot);
    // Les rappels qui ne font que jouer des sons, reconnus a l'export.
    const s = this.m.rappels_sons[f];
    if (s) {
      const ids = s.hasard ? [s.sons[this.moteur.rand() % 3]] : s.sons;
      for (const id of ids) this.son(id);
      return 0;
    }
    (this.inconnus ||= new Set()).add(f);
    return 0;
  }

  // $112C0 : un son, $Xnn = banque X, sequence nn.
  son(id) { this.moteur.sons.push({ banque: id >> 8, sequence: id & 0xFF }); }

  // $00F998 : la reaction du personnage a un point, lancee en mode 0.
  //   0 point quelconque, 1 le joueur gagne, 2 le joueur marque,
  //   3 l'adversaire marque, 4 l'adversaire gagne.
  reagir(n) {
    const s = this.m.adversaires[this.idx].reactions[n];
    if (s) this.lancer(s, 0);
  }

  // $00F778 : dessine l'image courante, puis avance. Renvoie 0 si le script
  // est termine et doit disparaitre.
  jouer(slot, dessiner) {
    const M = this.mem;
    let im = slot.cur;
    dessiner(M.w(im));
    dessiner(M.w(im + 8));
    if (slot.compte !== 0) { slot.compte--; return 1; }
    im += 10;
    if (M.w(im) === -2) {
      if (this.appeler(M.l(im + 4), slot)) return 1;   // on repassera ici
      im += 10;
    }
    if (M.w(im) >= -1) { this.entrer(slot, im); return 1; }
    if (slot.boucle) { this.entrer(slot, slot.start); return 1; }
    return 0;
  }

  // Placement d'un sprite du personnage, $00F690 avec le drapeau pose.
  // Le sprite 0 est le corps ; les autres sont places RELATIVEMENT a lui.
  // Renvoie [x gauche, y du BAS, rectangle a effacer ou null].
  placer(k) {
    const M = this.mem, t = this.table;
    const e = t + 8 * k;
    let h = M.w(e + 6);
    let x, yy;
    if (k === 0) { x = M.w(e) + 117; yy = M.w(e + 2); }
    else { x = M.w(t) + M.w(e) + 117; yy = M.w(t + 2) + M.w(e + 2); }
    const bas = yy + 67;
    if (yy > 0) { if (k !== 0) h -= yy; yy = 67; } else yy = bas;
    const efface = h > 1 ? [x, yy - h + 1, x + M.w(e + 4) - 1, yy] : null;
    return [x, bas, efface];
  }

  // Les fonctions de rappel des scripts, par adresse d'origine.
  definirRappels() {
    const mo = this.moteur, M = this.mem;
    const regard = (repos, gauche, centre, droite, autre) => {
      // Le personnage suit le palet des yeux pendant la poursuite et la frappe.
      if (mo.etatJeu !== 3) return -1;
      const e = mo.etatAdv;
      if (e === 0 || e === 6) return repos;
      if (e === 1 || e === 2) return mo.P.x < -83 ? gauche : (mo.P.x < 83 ? centre : droite);
      return autre;
    };
    const attente = (adresse) => () => { M.ecrire(adresse, mo.alea(30, 150)); return 0; };
    return {
      0xED4A: () => { M.ecrire(0x18812, regard(9, 5, 6, 7, 8)); return 0; },     // Skip
      0xEE0A: attente(0x188FA),                                                   // clignement
      0xEE2A: attente(0x18A84),
      0xEE4A: () => { M.ecrire(0x18AB4, regard(-1, 8, 10, 9, 5)); return 0; },
      0xEEBE: () => { M.ecrire(0x18D38, mo.alea(7, 16)); return 0; },            // Lexan
      0xEEDE: (slot) => {                                                         // Lexan : deux attentes
        const s = (mo.rand() & 1) ? 0x18D7E : 0x18D4C;
        slot.start = s;
        M.ecrire(s + 2, mo.alea(30, 150));
        return 0;
      },
      0xEF30: () => {                                   // Lexan se redresse
        if (M.w(0x18FC4) === 0) { mo.A.raquetteVisible = 1; return 0; }
        M.ecrire(0x1908C, M.w(0x1908C) - 1);
        M.ecrire(0x1908A, M.w(0x1908A) - M.w(0x1908C));
        M.ecrire(0x18FC4, M.w(0x1908A) >> 2);
        return 1;
      },
      0xEFE6: () => {                                   // Lexan s'effondre, raquette posee
        mo.A.raquetteVisible = 0;
        if (M.w(0x18FC4) > M.w(0x18FC8)) return 0;
        M.ecrire(0x18FC4, M.w(0x1908A) >> 2);
        M.ecrire(0x1908A, M.w(0x1908A) + M.w(0x1908C));
        M.ecrire(0x1908C, M.w(0x1908C) + 1);
        return 1;
      },
      0xF09E: attente(0x19090),
      0xF0BE: () => { M.ecrire(0x190C0, regard(-1, 10, 11, 12, 13)); return 0; },
      0xF132: attente(0x1958E),                                                   // Bejin
      0xF152: () => { mo.etatJeu = 6; return 0; },      // fin du service de Bejin : le palet part
      // $EDBE / $EDE0 : la voix de fin de partie, a 15 points.
      // RECONSTRUCTION : $1B596, qui peut l'empecher, est suppose nul.
      0xEDBE: () => { if (mo.s0 === 15) this.son(0x201); return 0; },
      0xEDE0: () => { this.son(mo.s1 === 15 ? 0x201 : 0x200); return 0; },
    };
  }
}
