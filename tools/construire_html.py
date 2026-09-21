#!/usr/bin/env python3
"""Assemble le prototype web en UN SEUL fichier HTML autonome.

Le resultat, dist/shufflepuck.html, s'ouvre d'un double-clic : pas de
serveur, pas de Python, pas de Node. Tout y est integre :

  - les modules JavaScript, chacun dans sa propre portee, dans l'ordre de
    leurs dependances ; un module ne voit que ce qu'il importe ;
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
IMPORT = re.compile(r"^import \{([^}]*)\} from '\./([\w.]+)';\s*$", re.M)


def imports(texte):
    """[(fichier, [noms])] des imports d'un texte."""
    return [(f, [n.strip() for n in noms.split(',') if n.strip()])
            for noms, f in IMPORT.findall(texte)]


def variable(fichier):
    return '__module_' + re.sub(r'\W', '_', fichier)


def lier(imps):
    """Les imports d'un module, relies aux modules deja evalues."""
    return '\n'.join('const { %s } = %s;' % (', '.join(noms), variable(f))
                     for f, noms in imps)


def main():
    page = open(os.path.join(WEB, 'index.html'), encoding='utf-8').read()
    debut = page.index('<script type="module">') + len('<script type="module">')
    fin = page.index('</script>', debut)
    script = page[debut:fin]

    # Les modules, dans l'ordre de leurs dependances.
    ordre, vus = [], set()
    def visiter(f):
        if f in vus:
            return
        vus.add(f)
        texte = open(os.path.join(WEB, f), encoding='utf-8').read()
        for dep, _ in imports(texte):
            visiter(dep)
        ordre.append(f)
    for f, _ in imports(script):
        visiter(f)

    morceaux = []
    for f in ordre:
        texte = open(os.path.join(WEB, f), encoding='utf-8').read()
        imps = imports(texte)
        texte = IMPORT.sub('', texte)
        exportes = re.findall(r'^export (?:class|function|const|let) (\w+)', texte, re.M)
        texte = re.sub(r'^export ', '', texte, flags=re.M)
        morceaux.append('// ===== %s =====\nconst %s = (() => {\n%s\n%s\nreturn { %s };\n})();'
                        % (f, variable(f), lier(imps), texte, ', '.join(exportes)))

    # La page : ses imports, puis son code.
    imps_page = imports(script)
    script = IMPORT.sub('', script)
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

    corps = '\n'.join([prelude] + morceaux + ['// ===== page =====', lier(imps_page), script])
    html = page[:debut] + '\n' + corps + '\n' + page[fin:]
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    open(SORTIE, 'w', encoding='utf-8').write(html)
    print('  %s : %d Ko, %d modules, %d fichiers integres'
          % (os.path.relpath(SORTIE, RACINE), len(html.encode('utf-8')) // 1024,
             len(ordre), len(donnees)))


if __name__ == '__main__':
    main()
