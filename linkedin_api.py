"""Connexion à LinkedIn : « Sign In with LinkedIn using OpenID Connect » et « Share on LinkedIn ».

Ces deux produits sont ouverts à toute application LinkedIn, sans validation. Ils permettent
de relier son compte (nom, photo) et de publier un post texte. Les statistiques des posts
personnels ne sont pas accessibles par l’API sans partenariat : elles s’importent depuis l’export.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

AUTH = 'https://www.linkedin.com/oauth/v2/authorization'
TOKEN = 'https://www.linkedin.com/oauth/v2/accessToken'
API = 'https://api.linkedin.com'
VERSION = '202607'  # version de l’API Posts (AAAAMM) ; LinkedIn garde chaque version environ un an
SCOPES = 'openid profile email w_member_social'


def configured():
    return bool(os.environ.get('LINKEDIN_CLIENT_ID') and os.environ.get('LINKEDIN_CLIENT_SECRET'))


def redirect_uri():
    """Adresse de retour après connexion : elle doit être déclarée à l’identique dans l’application LinkedIn."""
    return (os.environ.get('APP_URL') or 'http://localhost:8501').rstrip('/') + '/'


def auth_url(state):
    return AUTH + '?' + urllib.parse.urlencode(dict(response_type='code', client_id=os.environ['LINKEDIN_CLIENT_ID'], redirect_uri=redirect_uri(), state=state, scope=SCOPES))


def _call(req):
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read().decode() or '{}'
            return json.loads(body), dict(r.headers)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors='replace')[:300]
        raise RuntimeError(f'LinkedIn a refusé la demande ({e.code}). {detail}') from e
    except urllib.error.URLError as e:
        raise RuntimeError('LinkedIn est injoignable : vérifiez la connexion internet.') from e


def exchange(code):
    """Échange le code reçu au retour de LinkedIn contre un jeton d’accès (valable environ 60 jours)."""
    data = urllib.parse.urlencode(dict(grant_type='authorization_code', code=code, redirect_uri=redirect_uri(), client_id=os.environ['LINKEDIN_CLIENT_ID'], client_secret=os.environ['LINKEDIN_CLIENT_SECRET'])).encode()
    token, _ = _call(urllib.request.Request(TOKEN, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}))
    return token


def userinfo(access_token):
    info, _ = _call(urllib.request.Request(API + '/v2/userinfo', headers={'Authorization': 'Bearer ' + access_token}))
    return info


def _little_text(text):
    """Format « little text » de l’API Posts : caractères réservés échappés, hashtags convertis."""
    out = re.sub(r'([\\|{}@\[\]()<>*_~])', r'\\\1', text)
    out = re.sub(r'#(?!\w)', r'\\#', out)
    return re.sub(r'#(\w+)', lambda m: '{hashtag|\\#|' + m.group(1) + '}', out)


def publish(access_token, person_id, text):
    """Publie un post texte public sur le profil ; renvoie l’adresse du post."""
    body = dict(author='urn:li:person:' + person_id, commentary=_little_text(text), visibility='PUBLIC', lifecycleState='PUBLISHED', isReshareDisabledByAuthor=False,
                distribution=dict(feedDistribution='MAIN_FEED', targetEntities=[], thirdPartyDistributionChannels=[]))
    req = urllib.request.Request(API + '/rest/posts', data=json.dumps(body).encode(), method='POST', headers={
        'Authorization': 'Bearer ' + access_token, 'Content-Type': 'application/json', 'LinkedIn-Version': VERSION, 'X-Restli-Protocol-Version': '2.0.0'})
    _, headers = _call(req)
    urn = {k.lower(): v for k, v in headers.items()}.get('x-restli-id', '')
    return 'https://www.linkedin.com/feed/update/' + urn + '/' if urn else ''
