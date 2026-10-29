"""Rédacteur guidé : assemble un post LinkedIn à partir de vos ingrédients, sans IA.

Reprend les 21 formules d’accroche et la structure du skill li-post
(github.com/Jakeschincariol/linkedin-agent-skill, licence MIT), adaptées en français.
Rien n’est inventé : chaque phrase vient d’un champ que vous avez rempli.
"""
import re

# Champs du formulaire : clé, libellé, aide (exemple tiré de votre parcours)
FIELDS = {
    'fait': ('Ce qui s’est passé', 'Le fait concret, en une ou deux phrases. Ex. : nous avons comparé trois options et retenu la plus simple à expliquer.'),
    'contexte': ('Où, quand', 'Ex. : Dans mon dernier projet · Chez mon client · Pendant ma formation'),
    'chiffre': ('Le chiffre clé', 'Ex. : 3 réunions supprimées par semaine'),
    'points': ('Les étapes ou points clés (un par ligne)', 'Facultatif. 2 à 5 lignes courtes.'),
    'lecon': ('Ce que j’en retiens', 'La phrase qui recadre tout le reste. Ex. : Le plus simple à expliquer est souvent le plus simple à adopter.'),
    'produit': ('Le lien avec le produit', 'Facultatif. Ex. : Dans mon métier, je retrouve exactement cet arbitrage.'),
    'question': ('La question finale', 'Une question que seul ce post peut poser. Ex. : Quelle réunion supprimeriez-vous demain ?'),
    'hashtags': ('Hashtags (3 maximum)', 'Ex. : #Management #Méthode'),
}
EXTRA = {
    'croyance': ('Ce que tout le monde dit', 'Ex. : il faut toujours choisir l’outil le plus complet'),
    'pratique': ('Une pratique courante que vous remettez en cause (à l’infinitif)', 'Ex. : lancer un projet sans objectif écrit'),
    'cout': ('Ce que ça coûte', 'Ex. : deux semaines de développement'),
    'erreur': ('Une erreur que vous avez faite', 'Ex. : présenter les résultats avant de définir le succès'),
    'avant': ('Avant', 'Ex. : préparer un compte rendu me prenait une heure'),
    'apres': ('Après / aujourd’hui', 'Ex. : il me prend dix minutes'),
    'citation': ('Une phrase entendue', 'Ex. : Je veux quelque chose de plus fonctionnel.'),
    'experience': ('Votre expérience en années', 'Ex. : dix ans en agence'),
    'choix': ('Une décision qui allait contre l’évidence (à l’infinitif)', 'Ex. : garder les idées écartées au lieu de les supprimer'),
    'renoncement': ('Ce à quoi vous avez renoncé (au passé composé)', 'Ex. : arrêté le reporting hebdomadaire'),
    'ressource': ('Une ressource à partager', 'Ex. : la grille en 4 questions'),
    'objectif': ('À quoi sert cette ressource', 'Ex. : vérifier une synthèse IA'),
    'permission': ('Ce que le lecteur a le droit de faire', 'Ex. : présenter une hypothèse non concluante'),
    'bon': ('Ce que fait un bon professionnel', 'Ex. : livrent ce qui est demandé'),
    'excellent': ('Ce que fait un excellent professionnel', 'Ex. : vérifient d’abord le problème'),
    'role': ('Le métier visé', 'Ex. : chefs de projet'),
    'choc': ('Un mot ou une phrase-choc', 'Ex. : 63 %.'),
}

# id, nom, champs requis, gabarit, à quoi elle sert, le piège
HOOKS = [
    (1, 'Contre-pied', ['croyance', 'contexte'], 'On entend souvent : « {croyance} ». {contexte}, j’ai constaté l’inverse.', 'Affirmer un point de vue. Le meilleur taux de commentaires.', 'Contredire une idée que personne ne défend.'),
    (2, 'Le chiffre', ['chiffre', 'contexte'], '{chiffre}. {contexte}, voici ce qui s’est vraiment passé.', 'Expériences, défis, tout résultat qui se compte.', 'Enterrer le chiffre : il doit être en ligne 1.'),
    (3, 'L’erreur avouée', ['cout', 'erreur'], '{cout} : voilà ce que m’a coûté {erreur}.', 'La confiance. On partage les posts où l’on se montre faillible.', 'Une fausse erreur qui sert à se vanter.'),
    (4, 'Avant / après', ['avant', 'apres'], '{avant}. Aujourd’hui, {apres}. La différence tient en une chose.', 'Prouver le chemin parcouru.', 'Un avant trop flou pour être crédible.'),
    (5, 'La liste', ['points', 'contexte'], '{n} choses que j’ai apprises {contexte_lower}.', 'Les enregistrements, très valorisés par LinkedIn.', 'Une liste sans rien de neuf.'),
    (6, 'Le regard d’initiée', ['experience'], 'Après {experience}, voici ce qu’aucune fiche de poste ne dit.', 'Un avis appuyé sur l’expérience.', 'Ne marche que si les années sont réelles.'),
    (7, 'L’interpellation', ['pratique'], 'Si vous continuez à {pratique}, arrêtez.', 'Posts courts avec une seule consigne.', 'Donner un ordre sans le justifier ensuite.'),
    (8, 'La mise en situation', ['fait'], '{fait} Que feriez-vous ?', 'Le volume de commentaires : on répond à un scénario.', 'Un scénario sans enjeu réel.'),
    (9, 'Le dialogue', ['citation', 'contexte'], '« {citation} »\n\n{contexte}, cette phrase a tout changé.', 'Les récits longs. Le meilleur temps de lecture.', 'Une citation inventée ou trop générale.'),
    (10, 'La preuve', ['chiffre', 'fait'], '{chiffre}.', 'Tout ce que vous pouvez prouver. Doublez avec une image.', 'Un chiffre sans contexte.'),
    (11, 'Le faux coupable', ['croyance'], 'Non, {croyance_lower} n’explique pas tout.', 'Recadrer une explication répandue.', 'Ne pas livrer la vraie cause en ligne 3.'),
    (12, 'La comparaison', ['avant', 'apres'], '{avant}, ou {apres_lower} ? Le verdict m’a surprise.', 'Outils et méthodes. Très partagé.', 'Une comparaison sans verdict clair.'),
    (13, 'L’autorisation', ['permission'], 'Vous avez le droit de {permission}.', 'Toucher au-delà de votre niche.', 'Une permission que personne ne cherche.'),
    (14, 'La rupture', ['choc'], '{choc}', 'Arrêter le défilement. Le blanc fait le travail.', 'Une ligne 2 qui n’explique pas la ligne 1.'),
    (15, 'L’alerte', ['pratique', 'cout'], '{pratique_cap} vous coûte {cout}, sans bruit.', 'Un public qui n’a pas relié la cause au coût.', 'Exagérer le coût.'),
    (16, 'Bon ou excellent', ['role', 'bon', 'excellent'], 'Les bons {role} {bon}. Les excellents {role} {excellent}.', 'Phrases citables, faites pour la capture d’écran.', 'Un contraste trop faible.'),
    (17, 'L’ancre temporelle', ['avant', 'apres', 'fait'], 'Avant, {avant_lower}. Maintenant, {apres_lower}.', 'Outils, systèmes, méthodes : le meilleur format pour un mode d’emploi.', 'Un gain de temps impossible à croire.'),
    (18, 'La règle impopulaire', ['pratique'], 'Une règle que je tiens : ne jamais {pratique}. Voici pourquoi.', 'Se positionner, attirer les bons interlocuteurs.', 'Une règle sans raison.'),
    (19, 'Le paradoxe', ['choix'], 'Ma meilleure décision sur ce projet a été de {choix}.', 'Forcer le clic sur « voir plus ».', 'Un paradoxe qui n’en est pas un.'),
    (20, 'Le renoncement', ['renoncement', 'chiffre'], 'J’ai {renoncement}. Résultat : {chiffre_lower}.', 'Les valeurs, avec un résultat concret.', 'Un renoncement sans conséquence.'),
    (21, 'La ressource', ['ressource', 'objectif'], 'Voici exactement {ressource} que j’utilise pour {objectif}. Prenez-la.', 'Partager un outil. Le meilleur taux de conversion.', 'Promettre une ressource qu’on ne donne pas.'),
]
# Ordre de préférence : les accroches à chiffre et à récit d’abord, comme le recommande li-post
PRIORITY = [10, 2, 20, 17, 4, 3, 9, 1, 19, 6, 5, 15, 18, 11, 21, 8, 16, 12, 7, 13, 14]


def _clean(text):
    return re.sub(r'\s+', ' ', (text or '').strip())


def _cap(text):
    return text[:1].upper() + text[1:] if text else text


def _low(text):
    return text[:1].lower() + text[1:] if text and not text[:2].isupper() else text


def _end(text, mark='.'):
    text = _clean(text)
    return text if not text or text[-1] in '.!?…»:' else text + mark


def _slots(data):
    s = {k: _clean(v).rstrip('.') for k, v in data.items() if isinstance(v, str)}
    s['fait'] = _end(_cap(_clean(data.get('fait', ''))))
    for k in ('contexte', 'chiffre', 'pratique', 'croyance', 'avant', 'apres', 'cout'):
        if s.get(k):
            s[k] = _cap(s[k]) if k not in ('cout',) else s[k]
            s[k + '_lower'] = _low(s[k]); s[k + '_cap'] = _cap(s[k])
    pts = [p.strip(' -•▸→') for p in data.get('points', '').splitlines() if p.strip(' -•▸→')]
    s['n'] = str(len(pts)); s['points_list'] = pts
    return s


def hooks(data):
    """Les formules dont tous les ingrédients sont remplis, rendues avec vos mots."""
    s = _slots(data)
    ready = []
    for hid in PRIORITY:
        h = next(x for x in HOOKS if x[0] == hid)
        if all(s.get(k) for k in h[2]) and (hid != 5 or len(s['points_list']) >= 2):
            ready.append(dict(id=hid, name=h[1], text=h[3].format_map(s), used=h[2], best_for=h[4], trap=h[5]))
    return ready


def compose(data, hook):
    """Structure li-post : accroche, ligne 2 qui la paie, corps aéré, phrase pivot, une seule question."""
    s = _slots(data)
    used = {k for k in hook['used'] if s.get(k) and s[k].rstrip('.') in hook['text']}
    parts = [hook['text']]
    if 'fait' not in used and s['fait']:
        parts.append((s['contexte'] + ', ' + _low(s['fait'])) if s.get('contexte') and 'contexte' not in used else s['fait'])
    if s.get('chiffre') and 'chiffre' not in used:
        parts.append(_end(s['chiffre']))
    if s['points_list'] and len(s['points_list']) <= 6:
        parts.append(('Concrètement :' if hook['id'] != 5 else 'Les voici :') + '\n' + '\n'.join('- ' + _end(_cap(p)) for p in s['points_list']))
    if s.get('lecon'):
        parts.append(_end(_cap(s['lecon'])))
    if s.get('produit'):
        parts.append(_end(_cap(s['produit'])))
    if s.get('question'):
        parts.append(_end(_cap(_clean(data['question']))))  # question ou consigne : la ponctuation de l’autrice est gardée
    tags = re.findall(r'#\w+', data.get('hashtags', ''))[:3]
    if tags:
        parts.append(' '.join(tags))
    return '\n\n'.join(p for p in parts if p)


def checks(text, data):
    """Les règles de li-post et hooks.json, vérifiées sur le texte final."""
    first = text.split('\n', 1)[0]
    notes = []
    n = len(text)
    notes.append(('ok' if 900 <= n <= 1300 else 'warn', f'{n} caractères (zone de travail de li-post : 900 à 1 300).'))
    notes.append(('ok' if len(first) <= 140 else 'warn', f'Accroche de {len(first)} caractères (140 maximum pour rester visible sur mobile).'))
    notes.append(('ok' if re.search(r'\d', text) else 'warn', 'Un chiffre est présent.' if re.search(r'\d', text) else 'Aucun chiffre : les chiffres battent les adjectifs.'))
    if re.search(r'https?://', text):
        notes.append(('warn', 'Lien dans le texte : LinkedIn réduit la portée. Mettez-le en premier commentaire.'))
    q = text.count('?') - first.count('?')
    if q > 2:
        notes.append(('warn', f'{q} questions dans le corps : une seule question finale suffit.'))
    if not data.get('question', '').strip():
        notes.append(('warn', 'Pas de question finale : terminez par une question ou une consigne, jamais les deux.'))
    if len(re.findall(r'#\w+', text)) > 3:
        notes.append(('warn', 'Plus de 3 hashtags.'))
    return notes


def proofs(voice_text):
    """Les preuves utilisables listées dans voice.md, pour pré-remplir le formulaire."""
    m = re.search(r'## Proof I can use\s*(.*?)(\n## |\Z)', voice_text or '', flags=re.S)
    found = [l.strip('- ').strip() for l in (m.group(1) if m else '').splitlines() if l.strip().startswith('-')]
    return [p for p in found if p and not p.startswith('(')]  # ignore les consignes du modèle
