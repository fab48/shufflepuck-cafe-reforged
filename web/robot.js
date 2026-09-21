// robot.js — la main qui marque les points au tableau.
//
// Transcription de $00E262, appelee en tete du rendu de chaque image
// ($00F860). Une machine a etats sur $18438 deplace une main tenant une
// craie (sprite 0 de la banque « sprites ») ou une eponge (sprite 27) :
//
//   0  repos, cachee ; $E182 guette un score qui change
//   1  glisse en X vers la colonne du prochain baton, 5 px par image
//   2  puis en Y vers la ligne (joueur ou adversaire)
//   3  trace le baton : 3 pas de 2 px, ou 4 pas en diagonale pour le 5e
//   4  redescend jusqu'a Y = 90
//   5  sort par la gauche jusqu'a X = -60, puis se cache
//   6  eponge, aller : un score a BAISSE (nouvelle partie), on efface
//   7  eponge, retour, puis le score affiche est remis a zero
//
// Les batons sont traces dans le DECOR ($1B52E) : ils restent d'une image
// a l'autre. On garde donc un calque persistant du tableau, et une copie du
// tableau vierge pour l'eponge.
//
// La main est posee par le bas-gauche en (X, Y) ; la pointe de la craie est
// en (X + 48, Y - 45).

const LARG = 112, HAUT = 31;              // le tableau : sprite 1, pose en (0, 30)

export class Robot {
  constructor(m, moteur, interfaceImg, interfaceJson, couleur15, couleur0) {
    this.m = m; this.mo = moteur;
    this.img = interfaceImg; this.json = interfaceJson;
    this.c15 = couleur15; this.c0 = couleur0;
    this.decor = document.createElement('canvas');   // tableau + batons
    this.propre = document.createElement('canvas');  // tableau vierge
    for (const c of [this.decor, this.propre]) { c.width = LARG; c.height = HAUT + 1; }
    this.reinitialiser();
  }

  reinitialiser() {
    this.x = -60; this.y = 90;             // $18434, $18436
    this.etat = 0;                          // $18438
    this.sprite = -1;                       // $1843A
    this.affJoueur = 0; this.affAdv = 0;    // $1AF1E, $1AF20
    this.cible = 0; this.ligne = 0;         // $1AF1C, $1AF1A
    this.cote = 0;                          // $1B5B0 : 1 = ajouter, 0 = effacer
    this.pas = 0;                           // $1AF22
    this.champ = null;                      // $1AF24 : quel score affiche avance
    this.dessinerTableau(this.propre);
    this.dessinerTableau(this.decor);
  }

  // $00E0A6 : le tableau, et les deux noms.
  // RECONSTRUCTION : la fonte d'origine (quete.fnt) n'est pas extraite ; les
  // noms sont ecrits avec une fonte du navigateur, a la meme position.
  dessinerTableau(c) {
    const g = c.getContext('2d');
    g.imageSmoothingEnabled = false;
    g.fillStyle = this.c0; g.fillRect(0, 0, c.width, c.height);
    const s = this.json.sprites[1];
    g.drawImage(this.img, s.x, s.y, s.w, s.h, 0, 30 - s.h + 1, s.w, s.h);
    g.fillStyle = this.c15;
    g.font = '7px monospace';
    g.textBaseline = 'top';
    g.fillText('Visiteur', 5, 9);                                  // $14FA4 (5, 9)
    g.fillText(this.mo.A.nom, 5, 20);                  // +$52 du bloc, $14FA4 (5, 20)
  }

  // $00DFEC : l'abscisse du n-ieme baton. Groupes de cinq, 18 px par groupe,
  // 4 px par baton ; le cinquieme, en diagonale, part de 16 px plus a gauche.
  colonne(n) {
    const x = Math.trunc(n / 5) * 18 + 36;
    const r = n % 5;
    return r === 0 ? x - 16 : r * 4 + x + 1;
  }
  // $00E02E : l'ordonnee de la ligne.
  ligneY(decalage, n) { return decalage + 23 + (n % 5 === 0 ? 1 : 0); }

  // $00E182 : un score a-t-il change ?
  guetter() {
    const mo = this.mo;
    let bouge = false;
    if (this.affJoueur !== mo.s1) {
      this.cible = this.affJoueur + 1; this.champ = 'affJoueur'; this.ligne = -13;
      this.cote = this.affJoueur < mo.s1 ? 1 : 0; bouge = true;
    } else if (this.affAdv !== mo.s0) {
      this.cible = this.affAdv + 1; this.champ = 'affAdv'; this.ligne = -2;
      this.cote = this.affAdv < mo.s0 ? 1 : 0; bouge = true;
    }
    if (!bouge) return;
    if (this.cote) {
      if (this.sprite === 27) return;       // l'eponge travaille encore
      this.sprite = 0;
    } else {
      if (this.sprite === 0) return;        // la craie travaille encore
      this.sprite = 27;
    }
    this.etat = 1;
  }

  // Un trait de craie, double (x+48 et x+49), dans le decor.
  trait(x1, y1, x2, y2) {
    const g = this.decor.getContext('2d');
    g.strokeStyle = this.c15; g.lineWidth = 1;
    g.beginPath();
    for (const dx of [48, 49]) {
      g.moveTo(x1 + dx + 0.5, y1 - 45 + 0.5);
      g.lineTo(x2 + dx + 0.5, y2 - 45 + 0.5);
    }
    g.stroke();
  }

  // L'eponge : la bande de 4 lignes qu'elle a balayee redevient vierge.
  effacer(x, y, w) {
    if (w <= 0) return;
    this.decor.getContext('2d').drawImage(this.propre, x, y, w, 4, x, y, w, 4);
  }

  // $00E262
  image() {
    const diagonale = this.cible % 5 === 0;
    switch (this.etat) {
      case 0: this.guetter(); break;
      case 1: {
        const d4 = this.cote ? this.colonne(this.cible) : this.colonne(5);
        const a = this.x + 48, b = this.x + 53;
        if (a < d4 && b < d4) this.x += 5;
        else if (a > d4 && b > d4) this.x -= 5;
        else { this.x = d4 - 48; this.etat = 2; }
        break;
      }
      case 2: {
        const d5 = this.ligneY(this.ligne, this.cible);
        const a = this.y - 45, b = this.y - 50;
        if (a > d5 && b > d5) this.y -= 5;
        else if (a < d5 && b < d5) this.y += 5;
        else {
          this.y = d5 + 45;
          if (this.cote) { this.etat = 3; this.pas = diagonale ? 4 : 3; }
          else this.etat = 6;
        }
        break;
      }
      case 3: {
        const nx = diagonale ? this.x + 4 : this.x;
        const ny = diagonale ? this.y + 1 : this.y + 2;
        this.trait(this.x, this.y, nx, ny);
        this.x = nx; this.y = ny;
        if (--this.pas === 0) { this.etat = 4; this[this.champ]++; }
        break;
      }
      case 4:
        this.guetter();
        if (this.etat === 4) { if (this.y < 90) this.y += 5; else this.etat = 5; }
        break;
      case 5:
        this.guetter();
        if (this.etat === 5) {
          if (this.x > -60) this.x -= 5;
          else { this.etat = 0; this.sprite = -1; }
        }
        break;
      case 6: {                                     // l'eponge, vers la droite
        let d4 = this.x + 6;
        if (d4 + 48 > 96) d4 = 48;
        this.effacer(this.x + 48, this.y - 46, d4 - this.x + 1);
        this.x = d4;
        if (d4 === 48) { this.etat = 7; this.y += 3; }
        break;
      }
      case 7: {                                     // puis vers la gauche
        let d4 = this.x - 6;
        if (d4 + 48 < 36) d4 = -12;
        this.effacer(d4 + 48, this.y - 45, this.x - d4 + 1);
        this.x = d4;
        if (d4 === -12) { this.etat = 4; this[this.champ] = 0; }
        break;
      }
    }
  }

  // Le tableau dans le decor, puis la main par-dessus.
  dessiner(ctx) {
    ctx.drawImage(this.decor, 0, 0);
    if (this.sprite >= 0) {
      const s = this.json.sprites[this.sprite];
      ctx.drawImage(this.img, s.x, s.y, s.w, s.h, this.x, this.y - s.h + 1, s.w, s.h);
    }
  }
}
