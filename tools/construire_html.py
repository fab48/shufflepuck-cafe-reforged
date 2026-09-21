#!/usr/bin/env python3
"""Assemble le prototype web en UN SEUL fichier HTML autonome.

Le resultat, dist/shufflepuck.html, s'ouvre d'un double-clic : pas de
serveur, pas de Python, pas de Node. Tout y est integre :

  - les trois modules (moteur.js, animation.js, robot.js), mis bout a bout
    dans le script de la page, leurs import/export retires ;
  - chaque fichier de web/assets, encode en donnees (data:...).

Un navigateur refuse de charger des modules ou de faire des fetch() depuis
un fichier ouvert en local (file://). D'ou cette construction : plus rien
n'est charge de l'exterieur. Les appels fetch('assets/...') de la page sont
servis depuis les donnees integrees, et les images aussi.

    python tools/construire_html.py
"""
import os
import re
import json
import base64

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(RACINE, 'web')
SORTIE = os.path.join(RACINE, 'dist', 'shufflepuck.html')

TYPES = {'.png': 'image/png', '.json': 'application/json', '.wav': 'audio/wav'}


def module(nom, importes):
    """Un module dans sa propre portee ; seuls les noms que la page importe
    en sortent.

    Mis bout a bout sans cela, deux modules qui declarent le meme nom (w16
    existe dans moteur.js et dans la page) se heurtent.
    """
    texte = open(os.path.join(WEB, nom), encoding='utf-8').read()
    texte = re.sub(r'^import .*?;\s*$', '', texte, flags=re.M)
    exportes = re.findall(r'^export (?:class|function|const|let) (\w+)', texte, flags=re.M)
    texte = re.sub(r'^export ', '', texte, flags=re.M)
    manquants = set(importes) - set(exportes)
    if manquants:
        raise SystemExit('%s n\'exporte pas %s' % (nom, ', '.join(manquants)))
    noms = ', '.join(importes)
    return ('// ===== %s =====\nconst { %s } = (() => {\n%s\nreturn { %s };\n})();'
            % (nom, noms, texte, ', '.join(exportes)))


def main():
    page = open(os.path.join(WEB, 'index.html'), encoding='utf-8').read()
    debut = page.index('<script type="module">') + len('<script type="module">')
    fin = page.index('</script>', debut)
    script = page[debut:fin]
    # Ce que la page importe de chaque module.
    importes = {f: [n.strip() for n in noms.split(',')]
                for noms, f in re.findall(r"^import \{([^}]*)\} from '\./([\w.]+)';",
                                          script, flags=re.M)}
    script = re.sub(r'^import .*?;\s*$', '', script, flags=re.M)

    # Le chargement des images passe par les donnees integrees.
    ancien = 'i.src = src;'
    if ancien not in script:
        raise SystemExit("motif de chargement d'image introuvable dans index.html")
    script = script.replace(ancien, 'i.src = DONNEES[src] || src;')

    donnees = {}
    dossier = os.path.join(WEB, 'assets')
    for f in sorted(os.listdir(dossier)):
        ext = os.path.splitext(f)[1].lower()
        if ext not in TYPES:
            continue
        b64 = base64.b64encode(open(os.path.join(dossier, f), 'rb').read()).decode('ascii')
        donnees['assets/' + f] = 'data:%s;base64,%s' % (TYPES[ext], b64)

    prelude = (
        '// Tout est integre : aucun fichier n\'est charge de l\'exterieur.\n'
        'const DONNEES = %s;\n'
        'const _fetch = window.fetch.bind(window);\n'
        'window.fetch = (u, ...r) => {\n'
        '  const k = String(u).replace(/^\\.\\//, "").split("?")[0];\n'
        '  return DONNEES[k] ? _fetch(DONNEES[k]) : _fetch(u, ...r);\n'
        '};\n'
    ) % json.dumps(donnees)

    corps = '\n'.join([prelude] + [module(f, noms) for f, noms in importes.items()]
                      + ['// ===== page =====', script])
    html = page[:debut] + '\n' + corps + '\n' + page[fin:]
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    open(SORTIE, 'w', encoding='utf-8').write(html)
    print('  %s : %d Ko, %d fichiers integres'
          % (os.path.relpath(SORTIE, RACINE), len(html.encode('utf-8')) // 1024, len(donnees)))


if __name__ == '__main__':
    main()
