"""Copie les données locales (data/personnel) vers la base en ligne.

Lancer une fois, depuis ce dossier :  .venv/bin/python migrer_en_ligne.py
L’adresse de la base est lue dans .streamlit/secrets.toml (DATABASE_URL) ou dans l’environnement.
Les données locales ne sont ni modifiées ni supprimées. Relancer le script met à jour les fiches en ligne.
"""
import json
import os
import sqlite3
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / 'data' / 'personnel' / 'studio.sqlite3'
SECRETS = ROOT / '.streamlit' / 'secrets.toml'


def main():
    if not os.environ.get('DATABASE_URL') and SECRETS.exists():
        os.environ['DATABASE_URL'] = tomllib.loads(SECRETS.read_text()).get('DATABASE_URL', '')
    if not os.environ.get('DATABASE_URL'):
        sys.exit('DATABASE_URL introuvable : ajoutez-le dans .streamlit/secrets.toml (voir MISE-EN-LIGNE.md).')
    if not LOCAL.exists():
        sys.exit(f'Base locale introuvable : {LOCAL}')
    import storage as db  # importé après DATABASE_URL : il écrit donc dans la base en ligne
    db.init()
    src = sqlite3.connect(LOCAL)
    tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    counts = {}
    with db.connect() as c:
        for table in ('posts',) + db.ITEM_TABLES:
            rows = src.execute(f'SELECT id,payload FROM {table}').fetchall() if table in tables else []
            for id_, payload in rows:
                c.execute(f'INSERT INTO {table} VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (id_, payload))
            counts[table] = len(rows)
        for key, value in src.execute('SELECT key,value FROM meta').fetchall():
            c.execute('INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))
        rows = src.execute('SELECT id,favorite,notes FROM accounts').fetchall() if 'accounts' in tables else []
        for row in rows:
            c.execute('INSERT INTO accounts VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET favorite=excluded.favorite,notes=excluded.notes', row)
        counts['favoris et notes'] = len(rows)
        photos = list((ROOT / 'data' / 'personnel' / 'photos').glob('*.*'))
        for f in photos:
            c.execute('INSERT OR IGNORE INTO photos VALUES (?,?)', (f.name, f.read_bytes()))
        if 'photos' in tables:
            for id_, data in src.execute('SELECT id,data FROM photos').fetchall():
                c.execute('INSERT OR IGNORE INTO photos VALUES (?,?)', (id_, data))
                photos.append(id_)
        counts['photos'] = len(photos)
    db.save_voice(json.loads(src.execute("SELECT value FROM meta WHERE key='voice'").fetchone()[0]) if src.execute("SELECT 1 FROM meta WHERE key='voice'").fetchone() else (ROOT / 'data' / 'voix.md').read_text(encoding='utf-8'))
    print('Copié vers la base en ligne :')
    for k, v in counts.items():
        print(f'  {k} : {v}')
    print('  profil de voix : oui')


if __name__ == '__main__':
    main()
