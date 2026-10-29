"""Stockage persistant ; les données sources restent intactes.

En local : SQLite dans data/personnel. En ligne : Postgres (Supabase), dès que DATABASE_URL est défini.
"""
import hashlib
import io
import json
import csv
import os
import re
import sqlite3
import threading
import urllib.error
import urllib.request
from html import unescape
from urllib.parse import quote, urlparse
import uuid
import zipfile
from datetime import date, datetime
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('STUDIO_DATA_DIR', ROOT / 'data' / 'personnel'))
STATUSES = ['Idée', 'À rédiger', 'Texte prêt', 'Prêt', 'Publié']
# Piliers par défaut ; chacun les renomme dans l’onglet Personnalisation (apply_profile)
DEFAULT_PILLARS = {'A': 'Expertise métier', 'B': 'Méthodes et coulisses', 'C': 'Veille et outils', 'D': 'Projets et résultats', 'E': 'Parcours et opportunités'}
PILLARS = dict(DEFAULT_PILLARS)
IDEA_STATUSES = ['Brouillon', 'À retravailler', 'Prête à rédiger', 'Transformée en post', 'Écartée']
CONTENT_TYPES = ['Podcast', 'Livre', 'Article', 'Vidéo', 'Newsletter', 'Conférence', 'Formation']
# ideas : idées de posts · contents : contenus consommés · linkedin : statistiques importées
ITEM_TABLES = ('ideas', 'contents', 'linkedin')
PILLAR_KEYWORDS = {
    'A': ['décision', 'métrique', 'prévision', 'prévoir', 'priorisation', 'segmentation', 'hypothèse', 'kpi', 'engagement', 'succès', 'arbitrage', 'recommandation'],
    'B': ['client', 'clients', 'utilisateur', 'utilisateurs', 'parcours', 'expérience', 'design', 'interface', 'satisfaction', 'ux', 'usage'],
    'C': ['ia', 'intelligence artificielle', 'modèle', 'modèles', 'machine learning', 'arbre de décision', 'prédiction', 'agent', 'scikit-learn', 'classification'],
    'D': ['équipe', 'budget', 'parties prenantes', 'hackathon', 'répartition', 'contrainte', 'contraintes', 'rgpd', 'livrable', 'livrables', 'jury', 'coût'],
    'E': ['portfolio', 'profil', 'cv', 'candidature', 'parcours professionnel'],
}


class _Rows(list):
    def fetchone(self):
        return self[0] if self else None


class _Postgres:
    """Base en ligne avec la même interface que sqlite3 : une connexion partagée, réutilisée entre les pages."""
    lock = threading.Lock()
    con = None

    def execute(self, sql, params=()):
        sql = sql.replace('?', '%s')
        if sql.startswith('INSERT OR IGNORE'):
            sql = sql.replace('INSERT OR IGNORE', 'INSERT', 1) + ' ON CONFLICT DO NOTHING'
        sql = sql.replace(' BLOB', ' BYTEA')
        with self.lock:
            for attempt in (1, 2):
                try:
                    if _Postgres.con is None or _Postgres.con.closed:
                        import psycopg
                        from psycopg.rows import dict_row
                        _Postgres.con = psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row, autocommit=True, prepare_threshold=None, connect_timeout=15)
                    cur = _Postgres.con.execute(sql, params)
                    return _Rows(cur.fetchall() if cur.description else [])
                except Exception as e:
                    import psycopg
                    if attempt == 2 or not isinstance(e, psycopg.OperationalError):
                        raise
                    _Postgres.con = None  # connexion perdue (mise en veille, réseau) : on la rouvre une fois

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def online():
    return bool(os.environ.get('DATABASE_URL'))


def connect():
    if online():
        return _Postgres()
    DATA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DATA / 'studio.sqlite3', timeout=20)
    con.row_factory = sqlite3.Row
    return con


def research():
    """Benchmark, piliers et sujets : ceux de la base s’ils existent, sinon le modèle livré avec l’outil."""
    return get_meta('research') or json.loads((ROOT / 'data/recherche.json').read_text())


def profile():
    return get_meta('profile') or {}


def save_profile(data):
    set_meta('profile', data)
    apply_profile()


def apply_profile():
    PILLARS.clear()
    PILLARS.update(DEFAULT_PILLARS)
    PILLARS.update({k: v for k, v in profile().get('pillars', {}).items() if k in DEFAULT_PILLARS and v.strip()})


def init():
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS posts (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS accounts (id TEXT PRIMARY KEY, favorite INTEGER, notes TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS photos (id TEXT PRIMARY KEY, data BLOB NOT NULL)')
        for table in ITEM_TABLES:
            c.execute(f'CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        if not c.execute("SELECT 1 FROM meta WHERE key='seeded_v2'").fetchone() and (ROOT / 'data/amorce.json').exists():
            for table, rows in json.loads((ROOT / 'data/amorce.json').read_text()).items():
                for row in rows:
                    c.execute(f'INSERT OR IGNORE INTO {table} VALUES (?,?)', (row['id'], json.dumps(row, ensure_ascii=False)))
            c.execute("INSERT INTO meta VALUES ('seeded_v2','1')")
        if not c.execute("SELECT 1 FROM meta WHERE key='seeded'").fetchone() and (ROOT / 'data/publications.json').exists():
            for p in json.loads((ROOT / 'data/publications.json').read_text()):
                item = dict(id=p['id'], title=p['sujet'], body=p['body'], hooks=p['hooks'], date=p['date'], time=p['heure'], platform='LinkedIn', status='Texte prêt', pillar=p['pilier'], priority=p['priorite'], visual=p['visual'], alt='', photo='', notes='', published_url='', impressions=None, comments=None, leads=None, notion=p.get('url',''), sources=p['sources'], angle=p['properties']['Angle'])
                c.execute('INSERT OR IGNORE INTO posts VALUES (?,?)', (item['id'], json.dumps(item, ensure_ascii=False)))
            c.execute("INSERT INTO meta VALUES ('seeded','1')")
        if not c.execute("SELECT 1 FROM meta WHERE key='voice'").fetchone() and (ROOT / 'data/voix.md').exists():
            c.execute('INSERT INTO meta VALUES (?,?)', ('voice', json.dumps((ROOT / 'data/voix.md').read_text(encoding='utf-8'), ensure_ascii=False)))
    apply_profile()


def posts():
    with connect() as c:
        return sorted([json.loads(r['payload']) for r in c.execute('SELECT payload FROM posts')], key=lambda p: (p.get('date') or '9999', p.get('time',''),p['id']))


def save(item):
    if not item['title'].strip():
        raise ValueError('Donnez un titre à cette publication.')
    if item['status'] in ['Texte prêt', 'Prêt', 'Publié'] and not item['body'].strip():
        raise ValueError('Ajoutez un texte avant de choisir ce statut.')
    if item['published_url'] and not item['published_url'].startswith(('https://','http://')):
        raise ValueError('Le lien doit commencer par https:// ou http://.')
    item = dict(item, updated_at=datetime.now().astimezone().isoformat())
    with connect() as c:
        c.execute('INSERT INTO posts VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (item['id'], json.dumps(item,ensure_ascii=False)))
    return item


def new_post(title='', body='', sources='', platform='LinkedIn'):
    return dict(id='P-'+uuid.uuid4().hex[:10], title=title, body=body, hooks=[], date='', time='08:30', platform=platform, status='Idée', pillar='A', priority='Essentiel', visual='', alt='', photo='', notes='', published_url='', impressions=None, comments=None, leads=None, notion='', sources=sources, angle='PM / PO')


def save_photo(raw):
    if len(raw)>10*1024*1024:
        raise ValueError('Choisissez une image de moins de 10 Mo.')
    try:
        with Image.open(io.BytesIO(raw)) as im:
            im.verify()
        with Image.open(io.BytesIO(raw)) as im:
            fmt=im.format
            if fmt not in ['PNG','JPEG','WEBP']:
                raise ValueError('Utilisez une image PNG, JPEG ou WebP.')
    except Exception as e:
        raise ValueError('L’image est illisible ou son format n’est pas pris en charge.') from e
    name=hashlib.sha256(raw).hexdigest()+{'PNG':'.png','JPEG':'.jpg','WEBP':'.webp'}[fmt]
    with connect() as c:
        c.execute('INSERT OR IGNORE INTO photos VALUES (?,?)', (name, raw))
    return name


def photo_bytes(name):
    """L’image d’une publication : en base, ou dans l’ancien dossier photos/ des premières versions."""
    if not name or not re.fullmatch(r'[0-9a-f]{64}\.(png|jpg|webp)', name):
        return None
    with connect() as c:
        r=c.execute('SELECT data FROM photos WHERE id=?',(name,)).fetchone()
    if r:
        return bytes(r['data'])
    legacy=DATA/'photos'/name
    return legacy.read_bytes() if legacy.exists() else None


def account_state(id):
    with connect() as c:
        r=c.execute('SELECT favorite,notes FROM accounts WHERE id=?',(id,)).fetchone()
    return (bool(r['favorite']),r['notes']) if r else (False,'')


def accounts():
    with connect() as c:
        return {r['id']:(bool(r['favorite']),r['notes']) for r in c.execute('SELECT id,favorite,notes FROM accounts')}


def save_account(id, favorite, notes):
    with connect() as c:
        c.execute('INSERT INTO accounts VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET favorite=excluded.favorite,notes=excluded.notes',(id,int(favorite),notes))


def backup():
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('publications.json',json.dumps(posts(),ensure_ascii=False,indent=2))
        for table in ITEM_TABLES:
            z.writestr(table+'.json',json.dumps(items(table),ensure_ascii=False,indent=2))
        z.writestr('favoris-et-notes.json',json.dumps(accounts(),ensure_ascii=False,indent=2))
        with connect() as c:
            z.writestr('reglages.json',json.dumps({r['key']:r['value'] for r in c.execute('SELECT key,value FROM meta')},ensure_ascii=False,indent=2))
            for r in c.execute('SELECT id,data FROM photos'):
                z.writestr('photos/'+r['id'],bytes(r['data']))
        if not online():
            # Snapshot SQLite cohérent, même pendant une autre session.
            snap=sqlite3.connect(':memory:')
            with connect() as c:
                c.backup(snap)
            z.writestr('studio.sql','\n'.join(snap.iterdump())); snap.close()
        z.write(ROOT/'data/recherche.json','recherche.json')
    return out.getvalue()


def voice():
    return get_meta('voice') or ''


def save_voice(text):
    set_meta('voice', text)


# --- Idées, contenus et statistiques : même principe que les publications (id + JSON) ---

def items(table):
    assert table in ITEM_TABLES
    with connect() as c:
        rows=[json.loads(r['payload']) for r in c.execute(f'SELECT payload FROM {table}')]
    return sorted(rows, key=lambda r: r.get('created_at') or r.get('date') or '', reverse=True)


def save_item(table, item):
    assert table in ITEM_TABLES
    if table in ('ideas','contents') and not item.get('title','').strip():
        raise ValueError('Donnez un titre.')
    if item.get('url') and not item['url'].startswith(('https://','http://')):
        raise ValueError('Le lien doit commencer par https:// ou http://.')
    item=dict(item, updated_at=datetime.now().astimezone().isoformat())
    with connect() as c:
        c.execute(f'INSERT INTO {table} VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (item['id'], json.dumps(item,ensure_ascii=False)))
    return item


def delete_item(table, id):
    assert table in ITEM_TABLES
    with connect() as c:
        c.execute(f'DELETE FROM {table} WHERE id=?', (id,))


def new_idea(title='', note='', pillar='A', source='', url='', content_id='', repo=''):
    return dict(id='I-'+uuid.uuid4().hex[:10], title=title, note=note, pillar=pillar, status='Brouillon', source=source, url=url, content_id=content_id, repo=repo, tags='', post_id='', created_at=datetime.now().astimezone().isoformat())


def new_content(kind='Podcast'):
    return dict(id='C-'+uuid.uuid4().hex[:10], kind=kind, title='', author='', url='', date=date.today().isoformat(), takeaways='', quote='', tags='', pillar='A', created_at=datetime.now().astimezone().isoformat())


def get_meta(key, default=None):
    with connect() as c:
        r=c.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()
    return json.loads(r['value']) if r else default


def set_meta(key, value):
    with connect() as c:
        c.execute('INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value,ensure_ascii=False)))


def delete_meta(key):
    with connect() as c:
        c.execute('DELETE FROM meta WHERE key=?',(key,))


# --- LinkedIn : import de l'export officiel des statistiques (XLSX ou CSV) ---

METRICS = [('impression','impressions'),('membres atteints','reach'),('members reached','reach'),('engagement','engagements'),('interaction','engagements'),('réaction','reactions'),('reaction','reactions'),('comment','comments'),('republication','reposts'),('repost','reposts'),('partage','reposts'),('share','reposts'),('enregistrement','saves'),('save','saves'),('url','url'),('lien','url'),('date','date')]


def activity_id(url):
    m=re.search(r'(\d{16,20})', url or '')
    return m.group(1) if m else None


def _metric(header):
    h=str(header or '').strip().casefold()
    if not h or 'taux' in h or 'rate' in h: return None
    return next((key for word,key in METRICS if word in h), None)


def _number(v):
    if v is None or v=='': return None
    if isinstance(v,(int,float)): return int(v)
    v=re.sub(r'[\s\u202f\u00a0,]','',str(v))
    return int(float(v)) if re.fullmatch(r'-?\d+(\.\d+)?',v) else None


def _day(v, french):
    if isinstance(v,datetime): return v.date().isoformat()
    if isinstance(v,date): return v.isoformat()
    for fmt in (['%d/%m/%Y','%m/%d/%Y'] if french else ['%m/%d/%Y','%d/%m/%Y'])+['%Y-%m-%d']:
        try: return datetime.strptime(str(v).strip(),fmt).date().isoformat()
        except ValueError: pass
    return str(v or '')


def _sheets(raw, filename):
    if filename.lower().endswith('.csv'):
        text=raw.decode('utf-8-sig',errors='replace')
        return [list(csv.reader(io.StringIO(text), csv.Sniffer().sniff(text[:2048],',;\t')))]
    from openpyxl import load_workbook
    wb=load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    return [[list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets]


def parse_linkedin(raw, filename):
    """Retourne (publications, série quotidienne). Les tableaux sont repérés par leurs en-têtes, en français ou en anglais."""
    try: sheets=_sheets(raw, filename)
    except Exception as e: raise ValueError('Fichier illisible : utilisez l’export XLSX ou CSV de LinkedIn.') from e
    posts, daily = {}, {}
    for rows in sheets:
        i=0
        while i<len(rows):
            row=rows[i]
            keys=[_metric(h) for h in row]
            french=any(isinstance(h,str) and ('publication' in h.casefold() or 'interaction' in h.casefold()) for h in row)
            if 'url' in keys or ('date' in keys and 'impressions' in keys):
                # Un même en-tête peut porter plusieurs tableaux côte à côte (ex. onglet TOP POSTS).
                blocks=[]; start=None
                for j,k in enumerate(keys+[None]):
                    if k and start is None: start=j
                    if not k and start is not None: blocks.append((start,j)); start=None
                for line in rows[i+1:]:
                    if not any(v not in (None,'') for v in line): break
                    for a,b in blocks:
                        rec={}
                        for j in range(a,b):
                            k=keys[j]; v=line[j] if j<len(line) else None
                            if k=='url': rec['url']=str(v or '').strip()
                            elif k=='date': rec['date']=_day(v,french)
                            elif k: rec[k]=_number(v)
                        if rec.get('url'):
                            pid=activity_id(rec['url']) or rec['url']
                            posts.setdefault(pid,{}).update({k:v for k,v in rec.items() if v not in (None,'')})
                        elif 'url' not in keys[a:b] and rec.get('date'):
                            daily.setdefault(rec['date'],{}).update({k:v for k,v in rec.items() if v is not None})
                i+=1
            i+=1
    if not posts and not daily:
        raise ValueError('Aucun tableau de statistiques reconnu. Utilisez « Exporter » depuis les statistiques de vos posts LinkedIn.')
    return posts, daily


def import_linkedin(raw, filename):
    stats, daily = parse_linkedin(raw, filename)
    today=date.today().isoformat()
    known={r['id']:r for r in items('linkedin')}
    for pid,rec in stats.items():
        row=dict(known.get(pid) or dict(id=pid, title=''), **rec, collected=today, source=filename)
        save_item('linkedin', row)
    if daily:
        series=get_meta('linkedin_daily',{}); series.update(daily); set_meta('linkedin_daily',series)
    matched=0
    for p in posts():
        rec=stats.get(activity_id(p.get('published_url')))
        if rec:
            save(dict(p, impressions=rec.get('impressions',p.get('impressions')), comments=rec.get('comments',p.get('comments')), engagements=rec.get('engagements'), reactions=rec.get('reactions'), reposts=rec.get('reposts'), stats_updated=today))
            matched+=1
    return len(stats), len(daily), matched


# --- GitHub : dépôts et README via l’API publique (jeton facultatif pour les dépôts privés) ---

def _github(url, token, raw=False):
    req=urllib.request.Request(url, headers={'User-Agent':'studio-editorial', 'Accept':'application/vnd.github.raw' if raw else 'application/vnd.github+json', **({'Authorization':'Bearer '+token} if token else {})})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode('utf-8','replace') if raw else json.loads(r.read())


def github_sync(user, token=None):
    if not re.fullmatch(r'[A-Za-z0-9-]{1,39}', user or ''):
        raise ValueError('Indiquez un identifiant GitHub valide.')
    try:
        url='https://api.github.com/user/repos?per_page=100&sort=pushed' if token else f'https://api.github.com/users/{user}/repos?per_page=100&sort=pushed'
        repos=[r for r in _github(url, token) if not r['fork']]
        out=[]
        for r in repos:
            try: readme=_github(f"https://api.github.com/repos/{r['full_name']}/readme", token, raw=True)[:8000]
            except urllib.error.HTTPError: readme=''
            out.append(dict(name=r['name'], full_name=r['full_name'], url=r['html_url'], description=r['description'] or '', language=r['language'] or '', pushed_at=(r['pushed_at'] or '')[:10], private=r['private'], topics=r.get('topics',[]), readme=readme))
    except urllib.error.HTTPError as e:
        raise ValueError('GitHub refuse la requête ('+str(e.code)+'). Vérifiez l’identifiant ou le jeton, ou réessayez dans une heure.') from e
    except urllib.error.URLError as e:
        raise ValueError('GitHub est injoignable : vérifiez la connexion internet.') from e
    cache=dict(user=user, fetched_at=datetime.now().astimezone().isoformat(timespec='minutes'), repos=out)
    set_meta('github', cache)
    return cache


def _words(text):
    return {w for w in re.findall(r'[a-zà-ÿ]{5,}', text.casefold())}


def _results(readme):
    """Puces du README, de préférence dans une section « Résultats », sinon celles qui portent un chiffre clé."""
    bullets=[]; cur=None; section=''
    for line in readme.splitlines():
        text=line.strip()
        if text.startswith('#'): section=text.casefold(); cur=None
        elif re.match(r'([-*]|\d+\.) ',text): cur=[section,text.split(' ',1)[1]]; bullets.append(cur)
        elif text and cur and line.startswith(' '): cur[1]+=' '+text
        else: cur=None
    found=[b for sec,b in bullets if 'résultat' in sec or 'result' in sec] or [b for sec,b in bullets if re.search(r'\d ?(%|€|k€)',b)]
    return [b.replace('**','') for b in found][:4]


def repo_insights(repo, opportunities):
    """Piliers les plus proches, sujets recommandés liés et résultats repris du README."""
    text=(repo['name'].replace('-',' ')+' '+repo['description']+' '+repo['readme']).casefold()
    scores={k:sum(len(re.findall(r'(?<![\w-])'+re.escape(w)+r'(?![\w-])',text)) for w in words) for k,words in PILLAR_KEYWORDS.items()}
    pillars=[k for k,v in sorted(scores.items(), key=lambda x:-x[1]) if v][:2] or ['E']
    words=_words(text)
    topics=sorted(opportunities, key=lambda o:-len(_words(' '.join(o)) & words))[:2]
    return pillars, topics, _results(repo['readme'])


# --- Lien partagé depuis YouTube, Spotify, Apple Podcasts ou un article ---

def _fetch(url, as_json=False):
    req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 (studio-editorial)','Accept-Language':'fr-FR,fr;q=0.9'})
    with urllib.request.urlopen(req, timeout=10) as r:
        raw=r.read(600_000).decode('utf-8','replace')
    return json.loads(raw) if as_json else raw


def _meta_tag(page, name):
    m=re.search(r'<meta[^>]+(?:property|name)=["\']'+re.escape(name)+r'["\'][^>]*content=["\']([^"\']*)', page) or re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']'+re.escape(name)+'["\']', page)
    return unescape(m.group(1)).strip() if m else ''


def content_from_url(url):
    """Une fiche « contenu consommé » remplie à partir du lien : type, titre, auteur ou émission."""
    url=(url or '').strip()
    if not url.startswith(('https://','http://')):
        raise ValueError('Le lien partagé doit commencer par https://.')
    host=urlparse(url).netloc.lower()
    item=dict(new_content('Article'), url=url, takeaways='', tags='')
    try:
        if 'youtube.com' in host or 'youtu.be' in host:
            d=_fetch('https://www.youtube.com/oembed?format=json&url='+quote(url, safe=''), as_json=True)
            item.update(kind='Vidéo', title=d.get('title',''), author=d.get('author_name',''))
        elif 'spotify.com' in host:
            d=_fetch('https://open.spotify.com/oembed?url='+quote(url, safe=''), as_json=True)
            page=_fetch(url)
            item.update(kind='Podcast' if '/episode/' in url or '/show/' in url else 'Article', title=d.get('title',''), author=_meta_tag(page,'og:description').split(' · ')[0] if '/episode/' in url else '')
        elif 'podcasts.apple.com' in host:
            page=_fetch(url)
            title=_meta_tag(page,'og:title')
            show=re.search(r'/id(\d+)', url)
            author=''
            if show:
                found=_fetch('https://itunes.apple.com/lookup?id='+show.group(1), as_json=True).get('results',[])
                author=found[0].get('collectionName','') if found else ''
            item.update(kind='Podcast', title=title, author=author)
        else:
            page=_fetch(url)
            m=re.search(r'<title[^>]*>(.*?)</title>', page, flags=re.S|re.I)
            item.update(kind='Article', title=_meta_tag(page,'og:title') or (unescape(m.group(1)).strip() if m else ''), author=_meta_tag(page,'og:site_name') or _meta_tag(page,'author'))
    except (urllib.error.URLError, OSError, ValueError):
        pass  # hors ligne ou page protégée : la fiche est créée avec le lien, titre à compléter
    item['title']=re.sub(r'\s+',' ',item.get('title') or '').strip() or 'Contenu à compléter : '+host.replace('www.','')
    item['tags']='à trier'
    return item


def add_shared_link(url):
    """Ajoute le contenu partagé, sauf s’il est déjà dans la liste. Renvoie (fiche, déjà présent)."""
    known=next((c for c in items('contents') if c.get('url')==url.strip()), None)
    if known:
        return known, True
    return save_item('contents', content_from_url(url)), False
