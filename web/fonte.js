// fonte.js — la fonte d'origine (quete.fnt), telle que $14FA4 la trace.
//
// Seuls les pixels allumes du glyphe sont ecrits ; le fond reste. Le y
// designe la ligne du HAUT. Avance : largeur du glyphe (3 si elle est nulle,
// pour l'espace) + l'espacement global $1A710.

export function texte(g, fonte, chaine, x, y, couleur) {
  g.fillStyle = couleur;
  for (const ch of chaine) {
    const gl = fonte.glyphes[ch];
    const l = gl ? gl.l : 0;
    if (gl) {
      gl.p.forEach((ligne, dy) => {
        for (let dx = 0; dx < ligne.length; dx++)
          if (ligne[dx] === '1') g.fillRect(x + dx, y + dy, 1, 1);
      });
    }
    x += (l || 3) + fonte.espacement;
  }
}
