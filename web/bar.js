// bar.js — la scene du bar : l'ecran de choix de l'adversaire.
//
// Transcription de $01205A et de ce qu'il appelle :
//   - en entree, le script $18574 est lance en boucle (mode 1) : une seule
//     longue sequence de 55 images qui anime les clients a tour de role ;
//   - chaque image : le decor INTBAR ($ECD0), puis les animations ($FAA0,
//     banque « barsprit », placement ABSOLU a $18444), puis le nom du
//     champion en (40, 39) ($137D0) ;
//   - a chaque clic, la table de zones $1A040 est parcourue : un index
//     d'adversaire lance la partie, -2 est la bestiole (script $1879A, si
//     aucune autre animation ne joue), -1 la sortie ;
//   - la musique (banque 0, sequence 2) est relancee des qu'elle se termine
//     ($14EEC puis $11422).
//
// Le placement en mode absolu ($F690 sans le drapeau) : x, y du BAS,
// largeur, hauteur. Le rectangle est efface en noir avant de poser le
// sprite, comme pour les personnages.

import { Animations } from './animation.js';
import { texte } from './fonte.js';

export class Bar {
  constructor(m, moteur, fondImg, barImg, barJson, palette) {
    this.m = m;
    this.fond = fondImg; this.img = barImg; this.json = barJson;
    this.palette = palette;
    this.anim = new Animations(m, moteur);
  }

  entrer() {
    this.anim.mem.reinitialiser();
    this.anim.fond = []; this.anim.av = [];
    this.anim.lancer(this.m.bar.boucle, 1);
  }

  // Un sprite du bar, place en absolu.
  sprite(ctx, k) {
    if (k < 0) return;
    const M = this.anim.mem, e = this.m.bar.placement + 8 * k;
    const x = M.w(e), bas = M.w(e + 2), l = M.w(e + 4), h = M.w(e + 6);
    const s = this.json.sprites[k];
    if (!s) return;
    if (h > 1) {
      ctx.fillStyle = this.palette[0];
      ctx.fillRect(x, bas - h + 1, l, h);
    }
    ctx.drawImage(this.img, s.x, s.y, s.w, s.h, x, bas - s.h + 1, s.w, s.h);
  }

  // Une image de la scene.
  image(ctx) {
    ctx.drawImage(this.fond, 0, 0);
    const dessin = (k) => this.sprite(ctx, k);
    for (const s of this.anim.fond) this.anim.jouer(s, dessin);
    this.anim.av = this.anim.av.filter((s) => this.anim.jouer(s, dessin));
    texte(ctx, this.m.fonte, this.m.bar.champion, 40, 39, this.palette[15]);
  }

  // Un clic en coordonnees ecran (320 x 200). Renvoie un index d'adversaire,
  // ou null.
  clic(x, y) {
    for (const [x1, y1, x2, y2, v] of this.m.bar.zones) {
      if (x < x1 || x > x2 || y < y1 || y > y2) continue;
      if (v === -2) {
        if (this.anim.av.length === 0) this.anim.lancer(this.m.bar.bestiole, 0);
        return null;
      }
      if (v >= 0 && v <= 8) return v;
      return null;       // -1 la sortie, 9 l'enseigne : sans effet ici
    }
    return null;
  }

  // La zone survolee, pour le curseur.
  zone(x, y) {
    for (const z of this.m.bar.zones)
      if (x >= z[0] && x <= z[2] && y >= z[1] && y <= z[3]) return z[4];
    return null;
  }
}
