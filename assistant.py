"""Assistant LinkedIn : les skills li-* de Claude, utilisables depuis le studio via l’API Claude."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SKILLS = ROOT / 'skills'
VOICE = ROOT / 'data' / 'voix.md'
SOURCE = Path.home() / '.claude' / 'skills'
MODELS = {'claude-opus-5-5': 'Claude Opus 5.5 · meilleure qualité', 'claude-sonnet-5-5': 'Claude Sonnet 5.5 · plus rapide, moins cher', 'claude-haiku-5-5': 'Claude Haiku 5.5 · très économique'}
# Libellé, ce que fait le skill, et ce qu’il attend comme premier message
CATALOG = {
    'redaction-post-linkedin': ('Mon skill de rédaction', 'Écrit un post à partir d’une expérience vécue : accroche, compétence transférable, idées concrètes, conclusion en deux temps.', 'Racontez l’expérience dans l’ordre : déclencheur, réponses obtenues, conséquences.'),
    'li-post': ('Écrire un post', 'Trois accroches, un brouillon complet humanisé, en FR et EN.', 'Mon idée brute : ce qui s’est passé, pour qui, ce que ça a coûté ou rapporté…'),
    'li-human': ('Humaniser un texte', 'Retire les marques d’IA et réécrit les tournures signalées.', 'Collez le texte à humaniser.'),
    'li-carousel': ('Carrousel', 'Le texte de chaque slide et la couverture qui donne envie de swiper.', 'Le sujet ou la liste à transformer en carrousel.'),
    'li-repurpose': ('Recycler un contenu', 'Transforme un podcast, une vidéo ou un article en une semaine de posts.', 'Collez la transcription, les notes ou le résumé du contenu.'),
    'li-plan': ('Planifier la semaine', 'Quoi publier, quand, et avec qui interagir.', 'Ce qui se passe pour vous cette semaine, et vos disponibilités.'),
    'li-audit': ('Analyser mes résultats', 'Ce qui a marché, pourquoi, et ce qu’il faut arrêter.', 'Votre question, par exemple : « qu’est-ce qui marche dans mes posts ? »'),
    'li-profile': ('Noter mon profil', 'Score sur 100 et réécriture du titre, de l’Infos, des expériences.', 'Collez les sections de votre profil LinkedIn.'),
    'li-comment': ('Commenter un post', 'Des commentaires qui ont un avis, pas des réponses de robot.', 'Collez le post sur lequel vous voulez commenter.'),
    'li-reply': ('Répondre aux commentaires', 'Une réponse à chaque commentaire, triée par priorité.', 'Collez les commentaires reçus sous votre post.'),
    'li-dm': ('Message ou invitation', 'Note de connexion, premier message et relances.', 'À qui écrivez-vous, et pourquoi ?'),
    'li-inbox': ('Trier ma messagerie', 'Trie leads, recruteurs, pairs et spam, et rédige les réponses utiles.', 'Collez les messages et invitations à trier.'),
}
WRITING_SKILL = 'redaction-post-linkedin'
PERSONAL_WRITING = ('li-post', 'li-repurpose', 'li-carousel', 'redaction-post-linkedin')
ADAPTER = '''Tu es exécuté dans un Studio éditorial LinkedIn, une application Streamlit, et non dans Claude Code. La personne qui l’utilise est décrite dans voice.md et dans son profil (contexte du studio).
- Tu n’as ni outils, ni accès aux fichiers, ni commandes. Les fichiers que le skill demande de lire (voice.md, hooks.json, rubric.json, log.md, le skill li-human) sont fournis ci-dessous : utilise-les directement.
- Quand le skill demande de passer un texte dans /li-human, applique toi-même ses règles. Le studio exécute ensuite humanize.py et detect.py sur chaque bloc prêt à copier et affiche le score : n’invente pas de score.
- Le studio enregistre lui-même les textes retenus (idées, publications) : ne propose pas d’écrire dans log.md.
- Tu ne publies jamais rien. Réponds en français ; pour le tutoiement ou le vouvoiement des lecteurs, suis voice.md.
- Mets chaque texte prêt à copier dans son propre bloc ``` étiqueté FR ou EN sur la première ligne du bloc.
- N’invente aucun chiffre, client ou résultat : utilise uniquement les preuves de voice.md et le contexte fourni par le studio, sinon laisse {{à compléter}}.'''

IMPROVE = '''Voici un brouillon assemblé par le rédacteur guidé du studio, à partir des ingrédients que j’ai fournis. Améliore sa rédaction avec les skills li-post et li-human, sans rien ajouter de factuel.
Règles du studio, non négociables :
- Garde tous les faits et chiffres des ingrédients tels quels et n’en ajoute aucun. Ce qui manque reste {{{{à compléter}}}}.
- Garde l’accroche choisie, formule #{id} « {name} » : tu peux la resserrer, pas en changer.
- Accroche seule en ligne 1, 140 caractères maximum. La ligne 2 la justifie.
- 900 à 1 300 caractères, paragraphes de 1 à 3 lignes séparés par une ligne vide.
- Une phrase qui recadre, puis une seule question finale ou une consigne, jamais les deux.
- Aucun lien dans le texte, 3 hashtags maximum à la fin.
- Aucun tiret cadratin, aucun des mots que voice.md interdit.
Réponds avec un bloc ```FR puis un bloc ```EN, puis une ligne par modification importante.

## Ingrédients
{ingredients}

## Brouillon
{draft}'''


def improve_request(draft, data, hook):
    ingredients = '\n'.join(f'- {k} : {v.strip()}' for k, v in data.items() if v and v.strip())
    return IMPROVE.format(id=hook['id'], name=hook['name'], ingredients=ingredients, draft=draft)


def sync_skills():
    """Recopie les skills li-* et voice.md depuis ~/.claude, si Claude est installé sur cet ordinateur."""
    copied = []
    for src in sorted(SOURCE.glob('li-*')):
        shutil.copytree(src, SKILLS / src.name, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
        copied.append(src.name)
    voice = Path.home() / '.claude' / 'linkedin' / 'voice.md'
    if voice.exists():
        import storage
        shutil.copy(voice, VOICE)
        storage.save_voice(voice.read_text(encoding='utf-8'))
    return copied


def available():
    return [k for k in CATALOG if (SKILLS / k / 'SKILL.md').exists()]


def _skill_text(name):
    text = (SKILLS / name / 'SKILL.md').read_text(encoding='utf-8')
    return re.sub(r'^---.*?---\s*', '', text, count=1, flags=re.S)


def system_prompt(name):
    """Contenu stable (mis en cache) : adaptateur, skill, fichiers de référence, profil de voix."""
    parts = [ADAPTER, f'# Skill {name}\n\n{_skill_text(name)}']
    refs = {'li-post': ['li-post/hooks.json'], 'li-plan': ['li-post/hooks.json'], 'li-audit': ['li-post/hooks.json'], 'li-repurpose': ['li-post/hooks.json'], 'li-carousel': ['li-post/hooks.json'], 'li-profile': ['li-profile/rubric.json']}
    for ref in refs.get(name, []):
        if (SKILLS / ref).exists():
            parts.append(f'# Fichier {ref}\n\n' + (SKILLS / ref).read_text(encoding='utf-8'))
    # Règles de rédaction personnelles, appliquées à tous les textes de post (prioritaires sur les consignes génériques)
    if name in PERSONAL_WRITING and name != WRITING_SKILL and (SKILLS / WRITING_SKILL / 'SKILL.md').exists():
        parts.append(f'# Skill {WRITING_SKILL} (règles de rédaction de la personne : elles priment sur les consignes génériques ci-dessus en cas de conflit)\n\n{_skill_text(WRITING_SKILL)}')
    if name != 'li-human' and (SKILLS / 'li-human' / 'SKILL.md').exists():
        parts.append('# Skill li-human (à appliquer avant de montrer un texte)\n\n' + _skill_text('li-human'))
    import storage
    if storage.voice():
        parts.append('# Fichier voice.md (profil de voix de la personne)\n\n' + storage.voice())
    return '\n\n---\n\n'.join(parts)


def stream(name, messages, studio_context, model, api_key=None):
    """Génère la réponse au fil de l’eau. Le contexte du studio change souvent : il vient après le cache."""
    import anthropic  # facultatif : seul ce moteur en a besoin
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    system = [{'type': 'text', 'text': system_prompt(name), 'cache_control': {'type': 'ephemeral'}},
              {'type': 'text', 'text': '# Contexte du studio (données actuelles)\n\n' + studio_context}]
    extra = dict(betas=['server-side-fallback-2026-07-01'], fallbacks='default') if model != 'claude-haiku-5-5' else {}
    with client.beta.messages.stream(model=model, max_tokens=64000, system=system, messages=messages,
                                     thinking={'type': 'adaptive'}, output_config={'effort': 'high'}, **extra) as s:
        for text in s.text_stream:
            yield text
        final = s.get_final_message()
    if final.stop_reason == 'refusal':
        yield '\n\n_La demande a été refusée par les filtres de sécurité. Reformulez-la._'
    elif final.stop_reason == 'max_tokens':
        yield '\n\n_Réponse coupée : demandez la suite._'


def blocks(text):
    """Blocs prêts à copier : ```FR … ``` ou ```EN … ```, sinon tout bloc de code."""
    found = []
    for lang, body in re.findall(r'```([^\n`]*)\n(.*?)```', text, flags=re.S):
        label = lang.strip().upper()
        lines = body.strip('\n').split('\n')
        if not label and lines and lines[0].strip().upper() in ('FR', 'EN'):
            label = lines.pop(0).strip().upper()
        if '\n'.join(lines).strip():
            found.append((label or 'TEXTE', '\n'.join(lines).strip()))
    return found


def _run_tool(script, text):
    """Exécute un script du skill li-human sur le texte (entrée standard), en mode isolé."""
    out = subprocess.run([sys.executable, '-I', str(SKILLS / 'li-human' / script), '-', '--json'], input=text, capture_output=True, text=True, timeout=30)
    if out.returncode not in (0, 1) or not out.stdout.strip():
        raise RuntimeError(out.stderr.strip() or script + ' n’a rien renvoyé.')
    return json.loads(out.stdout)


def humanize(text):
    return _run_tool('humanize.py', text)


def detect(text):
    return _run_tool('detect.py', text)


def key_from_env():
    return bool(os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('ANTHROPIC_AUTH_TOKEN'))


def has_sdk():
    import importlib.util
    return importlib.util.find_spec('anthropic') is not None


def explain(error):
    """Message clair pour une erreur de l’API Claude."""
    name = type(error).__name__
    messages = {'AuthenticationError': 'Clé API invalide ou absente : vérifiez-la dans l’onglet Claude.',
                'RateLimitError': 'Limite de requêtes atteinte. Réessayez dans une minute.',
                'APIConnectionError': 'Connexion impossible à l’API Claude : vérifiez internet.'}
    if name in messages:
        return messages[name]
    if hasattr(error, 'status_code'):
        return f'Erreur de l’API Claude ({error.status_code}) : {getattr(error, "message", error)}'
    return str(error)
