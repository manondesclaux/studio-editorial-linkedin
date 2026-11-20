"""Lancer avec : python -m streamlit run app.py"""
import calendar
import csv
import hmac
import io
import json
import re
import time as _time
from datetime import date, datetime, time, timedelta
from html import escape
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
import os
import streamlit as st
# En ligne, les secrets (base de données, clé API) arrivent par st.secrets ; le stockage les lit dans l’environnement
try:
    for _k in ('DATABASE_URL','ANTHROPIC_API_KEY','GITHUB_TOKEN','LINKEDIN_CLIENT_ID','LINKEDIN_CLIENT_SECRET','APP_URL','APP_PASSWORD'):
        if _k in st.secrets and not os.environ.get(_k): os.environ[_k]=str(st.secrets[_k])
except Exception:
    pass
import assistant as ai
import linkedin_api as li
import redacteur as rd
import storage as db

st.set_page_config(page_title='Studio éditorial', page_icon='✦', layout='wide')


@st.cache_resource
def _login_failures():
    return []


def require_password():
    """Mot de passe facultatif (APP_PASSWORD) : indispensable dès que le studio est en ligne, car il peut publier sur LinkedIn."""
    expected=os.environ.get('APP_PASSWORD')
    if not expected or st.session_state.get('auth_ok'): return
    st.title('✦ Studio éditorial')
    with st.form('login'):
        given=st.text_input('Mot de passe',type='password')
        entered=st.form_submit_button('Entrer',type='primary')
    if entered:
        now=_time.time(); failures=_login_failures(); failures[:]=[t for t in failures if now-t<300]
        if len(failures)>=5: st.error('Trop d’essais. Réessayez dans quelques minutes.')
        elif hmac.compare_digest(given.encode(),expected.encode()): st.session_state['auth_ok']=True; st.rerun()
        else: failures.append(now); st.error('Mot de passe incorrect.')
    st.stop()


require_password()
db.init()
# Identité de marque : beige clair, beige foncé, marron, noir, blanc
st.markdown('''<style>
:root{--beige:#F4EEE4;--beige-fonce:#E2D3BD;--marron:#6B4A33;--noir:#1C1A17;--blanc:#FFFFFF}
.stApp {background:var(--beige)} h1,h2,h3 {color:var(--noir)} h1{border-bottom:2px solid var(--marron);padding-bottom:.3em}
a,a:visited{color:var(--marron)!important;text-decoration:underline;text-underline-offset:2px} a:hover{color:var(--noir)!important}
[data-testid="stSidebar"]{background:var(--beige-fonce)} [data-testid="stSidebar"] h1{color:var(--marron);border:none}
[data-testid="stMetric"]{background:var(--blanc);padding:16px;border-radius:14px;border:1px solid var(--beige-fonce)}
[data-testid="stMetricValue"]{color:var(--marron)}
[data-testid="stExpander"],[data-testid="stVerticalBlockBorderWrapper"]{background:var(--blanc)}
.calendar-day{background:var(--blanc);min-height:142px;padding:10px;border-radius:12px;border:1px solid var(--beige-fonce);margin-bottom:10px}
.calendar-day a{display:block;background:var(--beige);border-left:3px solid var(--marron);padding:7px;margin-top:7px;font-size:13px;border-radius:4px}
.calendar-day.today{border:2px solid var(--marron);background:var(--beige-fonce);box-shadow:0 0 0 3px rgba(107,74,51,.15)} .calendar-day.today a{background:var(--blanc)} .today-badge{display:block;width:fit-content;max-width:100%;margin-top:4px;background:var(--marron);color:var(--blanc);border-radius:10px;padding:1px 7px;font-size:11px;font-weight:600;line-height:1.3;white-space:normal;overflow-wrap:anywhere}
.calendar-day.muted{opacity:.4} .month-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px} .month-grid a{overflow-wrap:anywhere} .agenda-mobile{display:none} @media(max-width:700px){.month-grid{display:none}.agenda-mobile{display:block}} .label{color:var(--marron);font-size:12px;text-transform:uppercase;letter-spacing:.1em}
.tag{display:inline-block;background:var(--beige-fonce);color:var(--noir);border-radius:10px;padding:1px 9px;margin:0 4px 4px 0;font-size:12px}
</style>''',unsafe_allow_html=True)
PAGES=['Vue d’ensemble','Personnalisation','Mon compte LinkedIn','Calendrier','Publications','Nouvelle publication','Assistant LinkedIn','Idées de posts','Contenus consommés','GitHub','Impact LinkedIn','Benchmark international','Sujets & stratégie','Sauvegardes']
SUGGESTIONS=dict(
    metiers=['Product Owner','Product Manager','Chef de projet IT','UX designer','Data analyst','Consultant','Entrepreneur','Freelance','Développeur','Marketing','Recruteur'],
    interests=['Produit','IA','Design','Data','Entrepreneuriat','Management','Tech','Marketing','Écologie','Sport','Voyage','Lecture'],
    skills_pro=['Discovery','Priorisation','Gestion de projet','Analyse de données','UX','Prototypage','Facilitation','Négociation','Rédaction','SQL','Python','Figma'],
    skills_perso=['Écoute','Curiosité','Rigueur','Créativité','Pédagogie','Autonomie','Esprit d’équipe','Adaptabilité','Leadership','Persévérance'])
ICONS={'Podcast':'🎧','Livre':'📖','Article':'📰','Vidéo':'▶️','Newsletter':'✉️','Conférence':'🎤','Formation':'🎓'}
ANGLES={'A':'La décision derrière « {n} » : quelle question, quelle métrique, quel arbitrage',
        'B':'Ce que « {n} » m’a appris sur les personnes derrière les données',
        'C':'Ce qu’un modèle peut éclairer, et ce qu’il ne doit pas décider seul : « {n} »',
        'D':'Contraintes, équipe et livrables : comment nous avons cadré « {n} »',
        'E':'Ce que « {n} » montre de ma façon de contribuer à une équipe produit'}
TODAY=datetime.now(ZoneInfo('Europe/Paris')).date()
MONTHS=['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']
DAYS=['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche']

def goto(page,post=None):
    st.query_params.clear(); st.query_params['page']=page
    if post: st.query_params['post']=post
    st.rerun()

def href(page,post=None):
    return '?'+urlencode(dict(page=page,**({'post':post} if post else {})))

def post_link(p):
    return '<a target="_self" href="'+escape(href('Publications',p['id']),quote=True)+'">'+escape(p['title'])+'</a>'

def flash():
    msg=st.session_state.pop('notice',None)
    if msg: st.success(msg)

def tags(text):
    return ''.join('<span class="tag">'+escape(t.strip())+'</span>' for t in (text or '').split(',') if t.strip())

def _low_first(text):
    return text[:1].lower()+text[1:] if text else text

@st.cache_data(show_spinner=False)
def human_score(text):
    return ai.detect(text)

def idea_to_post(idea):
    draft=db.new_post(idea['title'],sources=idea.get('url',''))
    draft.update(pillar=idea['pillar'],notes=idea['note']+('\nOrigine : '+idea['source'] if idea.get('source') else ''),from_idea=idea['id'])
    st.session_state['draft']=draft;goto('Nouvelle publication')

# Lien envoyé depuis le menu Partager du téléphone (raccourci « Ajouter au studio ») : ?ajout=<lien>
# Retour de LinkedIn après « Se connecter avec LinkedIn » : ?code=…&state=…
if st.query_params.get('state') and (st.query_params.get('code') or st.query_params.get('error')):
    expected=db.get_meta('linkedin_state')
    if st.query_params.get('error'): st.session_state['notice']='Connexion LinkedIn annulée.'
    elif not expected or not hmac.compare_digest(str(st.query_params['state']).encode(),str(expected).encode()): st.session_state['notice']='Connexion LinkedIn refusée : lien expiré ou invalide. Recommencez depuis l’onglet Mon compte LinkedIn.'
    else:
        try:
            token=li.exchange(st.query_params['code']); info=li.userinfo(token['access_token'])
            db.set_meta('linkedin_auth',dict(access_token=token['access_token'],expires_at=(datetime.now()+timedelta(seconds=int(token.get('expires_in',0)))).isoformat(timespec='minutes'),
                                             sub=info.get('sub',''),name=info.get('name',''),picture=info.get('picture',''),email=info.get('email','')))
            prof=db.profile()
            if not prof.get('name') and info.get('name'): db.save_profile(dict(prof,name=info['name']))
            st.session_state['notice']='Compte LinkedIn connecté : '+info.get('name','')
        except RuntimeError as e: st.session_state['notice']=str(e)
    db.delete_meta('linkedin_state')
    goto('Mon compte LinkedIn')

if st.query_params.get('ajout'):
    shared=st.query_params['ajout']
    try:
        with st.spinner('Lecture du lien partagé…'): item,known=db.add_shared_link(shared)
        st.session_state['notice']=('Déjà dans vos contenus : ' if known else 'Ajouté à vos contenus : ')+item['title']
        st.session_state['just_added']=item['id']
    except ValueError as e: st.session_state['notice']=str(e)
    goto('Contenus consommés')

all_posts=db.posts(); research=db.research(); profile=db.profile(); li_auth=db.get_meta('linkedin_auth')
ideas=db.items('ideas'); contents=db.items('contents'); li_stats=db.items('linkedin')
content_label={c['id']:ICONS.get(c['kind'],'')+' '+c['title'] for c in contents}
page=st.query_params.get('page',PAGES[0])
if page not in PAGES: page=PAGES[0]
with st.sidebar:
    st.title('✦ Studio éditorial')
    if db.online() and not os.environ.get('APP_PASSWORD'):
        st.warning('Studio en ligne sans mot de passe : ajoutez APP_PASSWORD dans les secrets (voir MISE-EN-LIGNE.md).')
    st.caption(' · '.join(x for x in [profile.get('name',''),' / '.join(profile.get('metiers',[]))] if x) or 'Complétez votre profil dans Personnalisation')
    for nav in PAGES:
        if st.button(nav,width='stretch',type='primary' if page==nav else 'secondary'):
            goto(nav)
    st.divider()
    st.caption('Base en ligne · mêmes données sur le téléphone et l’ordinateur' if db.online() else 'Espace local · données conservées sur cet ordinateur')
    st.caption('Statistiques LinkedIn importées depuis l’export officiel ; GitHub synchronisé à la demande. Vos données restent dans votre propre base.')

st.title(page)
flash()

if page=='Vue d’ensemble':
    st.write('Du sujet à la publication : préparez vos textes, planifiez vos créneaux et retrouvez vos inspirations.')
    if not profile.get('name'):
        with st.container(border=True):
            st.markdown('**Bienvenue dans votre studio éditorial.** Trois étapes pour démarrer :')
            st.markdown('1. **Personnalisation** : présentez-vous, vos métiers et vos piliers éditoriaux.\n2. **Mon compte LinkedIn** : reliez votre compte, puis importez vos statistiques.\n3. **Assistant LinkedIn** : notez une idée et laissez le rédacteur guidé construire votre premier post.')
            if st.button('Commencer par la personnalisation',type='primary'): goto('Personnalisation')
    cols=st.columns(4)
    for c,(name,value) in zip(cols,[('Publications',len(all_posts)),('Textes préparés',sum(p['status'] in ['Texte prêt','Prêt'] for p in all_posts)),('Comptes analysés',len(research['benchmark'])),('Publiées',sum(p['status']=='Publié' for p in all_posts))]): c.metric(name,value)
    cols=st.columns(4)
    imp=sum(r.get('impressions') or 0 for r in li_stats); eng=sum(r.get('engagements') or 0 for r in li_stats)
    for c,(name,value) in zip(cols,[('Idées à retravailler',sum(i['status'] in db.IDEA_STATUSES[:3] for i in ideas)),('Contenus consommés',len(contents)),('Impressions LinkedIn suivies',f'{imp:,}'.replace(',',' ')),('Taux d’engagement',f'{100*eng/imp:.2f} %'.replace('.',',') if imp else '–')]): c.metric(name,value)
    st.subheader('Les prochaines publications')
    upcoming=[p for p in all_posts if p.get('date') and p['date']>=TODAY.isoformat() and p['status']!='Publié'][:5]
    if not upcoming: st.info('Aucune publication à venir. Ajoutez une date dans une fiche.')
    for p in upcoming:
        with st.container(border=True):
            st.caption(f"{DAYS[date.fromisoformat(p['date']).weekday()]} {date.fromisoformat(p['date']).strftime('%d/%m/%Y')} · {p['time']} Paris · {p['platform']} · {p['status']}")
            st.markdown(post_link(p),unsafe_allow_html=True)
            st.write(p['body'][:180]+('…' if len(p['body'])>180 else ''))
    st.info('Ouvrez une fiche pour modifier le texte et ajouter une photo. Le passage au statut Publié sert au suivi ; vous publiez vous-même sur la plateforme.')

elif page=='Calendrier':
    c1,c2,c3=st.columns([2,1,1])
    platforms=['Toutes']+sorted({p['platform'] for p in all_posts})
    platform=c1.selectbox('Plateforme',platforms)
    year=c2.number_input('Année',2020,2100,max(2020,min(2100,TODAY.year)))
    month=c3.selectbox('Mois',range(1,13),index=TODAY.month-1,format_func=lambda x:MONTHS[x-1])
    essentials=st.checkbox('Afficher seulement les posts essentiels')
    selected=[p for p in all_posts if (platform=='Toutes' or p['platform']==platform) and (not essentials or p['priority']=='Essentiel')]
    html='<div class="month-grid">'+''.join('<b>'+d+'</b>' for d in DAYS)
    for week in calendar.Calendar().monthdatescalendar(int(year),month):
        for day in week:
            cards=[p for p in selected if p.get('date')==day.isoformat()]
            html+='<div class="calendar-day'+(' muted' if day.month!=month else '')+(' today' if day==TODAY else '')+'"><b>'+str(day.day)+'</b>'+('<span class="today-badge">Aujourd’hui</span>' if day==TODAY else '')
            for p in cards: html+=post_link(dict(p,title=f"{p['time']} · {p['title']}"))+'<span class="label">'+escape(p['status'])+'</span>'
            html+='</div>'
    html+='</div><div class="agenda-mobile">'
    mobile=[p for p in selected if p.get('date') and p['date'].startswith(f'{int(year):04d}-{month:02d}')]
    for p in mobile:
        d=date.fromisoformat(p['date'])
        html+='<div class="calendar-day'+(' today' if d==TODAY else '')+'"><b>'+DAYS[d.weekday()]+' '+d.strftime('%d/%m')+' · '+escape(p['time'])+'</b>'+post_link(p)+'<span class="label">'+escape(p['status'])+'</span></div>'
    html+=('</div>' if mobile else 'Aucun post prévu ce mois-ci.</div>')
    st.markdown(html,unsafe_allow_html=True)
    st.caption('Cliquez sur un titre pour ouvrir sa page. Dates et horaires modifiables dans chaque fiche ; fuseau Europe/Paris.')
    undated=[p for p in selected if not p.get('date')]
    if undated:
        st.subheader('À planifier')
        for p in undated: st.markdown(post_link(p),unsafe_allow_html=True)

elif page in ['Publications','Nouvelle publication']:
    pid=st.query_params.get('post')
    current=next((p for p in all_posts if p['id']==pid),None)
    if page=='Publications' and not current:
        c1,c2,c3=st.columns(3)
        q=c1.text_input('Rechercher un sujet ou un texte')
        platform=c2.selectbox('Plateforme',['Toutes']+sorted({p['platform'] for p in all_posts}))
        status=c3.selectbox('Statut',['Tous']+db.STATUSES)
        view=st.radio('Présentation',['Liste','Production','Galerie'],horizontal=True)
        chosen=[p for p in all_posts if q.casefold() in (p['title']+' '+p['body']).casefold() and (platform=='Toutes' or p['platform']==platform) and (status=='Tous' or p['status']==status)]
        if view=='Production':
            for col,s in zip(st.columns(5),db.STATUSES):
                with col:
                    st.markdown('**'+s+'**')
                    for p in chosen:
                        if p['status']==s:
                            with st.container(border=True):
                                st.markdown(post_link(p),unsafe_allow_html=True);st.caption(p['date'] or 'À planifier')
        elif view=='Galerie':
            cols=st.columns(3)
            for i,p in enumerate(chosen):
                with cols[i%3],st.container(border=True):
                    photo=db.photo_bytes(p.get('photo',''))
                    if photo: st.image(photo,width='stretch')
                    else: st.caption('Photo à ajouter · facultative')
                    st.markdown(post_link(p),unsafe_allow_html=True);st.caption(p['status'])
        else:
            for p in chosen:
                with st.container(border=True):
                    st.markdown(post_link(p),unsafe_allow_html=True)
                    st.caption(f"{p.get('date') or 'À planifier'} · {p['time']} · {p['platform']} · {p['status']} · {p['priority']}")
        if not chosen: st.info('Aucune publication ne correspond à ces filtres.')
    else:
        p=current or st.session_state.get('draft') or db.new_post()
        if not current: st.session_state['draft']=p
        st.subheader(p['title'] or 'Votre prochaine publication')
        if current:
            left,right=st.columns(2)
            if left.button('← Toutes les publications'): goto('Publications')
            if right.button('Dupliquer pour une autre publication'):
                clone=db.new_post(p['title']+' · copie',p['body'],p['sources'],p['platform']); clone.update(hooks=p['hooks'],visual=p['visual'],pillar=p['pillar'],angle=p['angle'])
                st.session_state['draft']=clone;goto('Nouvelle publication')
        with st.form('editor-'+p['id']):
            title=st.text_input('Sujet',p['title'])
            c1,c2,c3=st.columns(3)
            platform=c1.text_input('Plateforme',p['platform'],help='LinkedIn pour commencer ; ajoutez un autre nom si besoin.')
            planned=c2.checkbox('Prévoir une date',bool(p.get('date')))
            day=c2.date_input('Jour de publication',date.fromisoformat(p['date']) if p.get('date') else TODAY)
            hour=c3.time_input('Heure de Paris',time.fromisoformat(p['time']))
            c1,c2,c3=st.columns(3)
            status=c1.selectbox('Statut',db.STATUSES,index=db.STATUSES.index(p['status']))
            priority=c2.selectbox('Priorité',['Essentiel','Optionnel'],index=['Essentiel','Optionnel'].index(p['priority']))
            pillar=c3.selectbox('Pilier',list(db.PILLARS),format_func=lambda x:db.PILLARS[x],index=list(db.PILLARS).index(p['pillar']))
            body=st.text_area('Texte de la publication',p['body'],height=400)
            st.caption('Les accroches alternatives sont disponibles sous le formulaire. Le premier paragraphe du texte est l’accroche retenue.')
            upload=st.file_uploader('Ajouter ou remplacer la photo (10 Mo maximum)',type=['png','jpg','jpeg','webp'])
            remove=st.checkbox('Retirer la photo actuelle') if p.get('photo') else False
            alt=st.text_input('Description de l’image pour l’accessibilité',p.get('alt',''))
            visual=st.text_area('Idée de visuel',p['visual'])
            notes=st.text_area('Notes de préparation',p['notes'])
            sources=st.text_area('Sources et inspirations',p['sources'])
            published=st.text_input('Lien de la publication en ligne',p['published_url'])
            st.caption('Mesures à J+7 · laissez vide tant qu’elles ne sont pas relevées.')
            metrics=st.columns(3)
            imp=metrics[0].number_input('Impressions',min_value=0,value=p.get('impressions'),step=1)
            comments=metrics[1].number_input('Commentaires externes',min_value=0,value=p.get('comments'),step=1)
            leads=metrics[2].number_input('Messages qualifiés',min_value=0,value=p.get('leads'),step=1)
            submitted=st.form_submit_button('Enregistrer la publication',type='primary')
        if submitted:
            try:
                if not platform.strip(): raise ValueError('Indiquez une plateforme.')
                photo='' if remove else p.get('photo','')
                if upload: photo=db.save_photo(upload.getvalue())
                saved=dict(p,title=title,body=body,date=day.isoformat() if planned else '',time=hour.strftime('%H:%M'),platform=platform.strip(),status=status,priority=priority,pillar=pillar,photo=photo,alt=alt,visual=visual,notes=notes,sources=sources,published_url=published.strip(),impressions=imp,comments=comments,leads=leads)
                db.save(saved);st.session_state.pop('draft',None);st.session_state['notice']='Publication enregistrée.'
                idea=next((i for i in ideas if i['id']==p.get('from_idea')),None)
                if idea and not idea.get('post_id'): db.save_item('ideas',dict(idea,status='Transformée en post',post_id=p['id']))
                goto('Publications',p['id'])
            except ValueError as e: st.error(str(e))
        if p['hooks']:
            with st.expander('Trois accroches au choix'):
                for i,h in enumerate(p['hooks'],1): st.write(f'{i}. {h}')
        st.subheader('Texte à copier · version enregistrée')
        st.code(p['body'] or 'Le texte apparaîtra ici après enregistrement.',language=None,wrap_lines=True)
        st.download_button('Télécharger le texte',p['body'],file_name=p['id']+'.txt',mime='text/plain')
        photo=db.photo_bytes(p.get('photo',''))
        if photo: st.image(photo,caption=p.get('alt') or 'Visuel de la publication',width=500)
        if p.get('notion'): st.link_button('Consulter la fiche Notion initiale',p['notion'])
        if p.get('stats_updated'):
            st.caption(f"Statistiques LinkedIn importées le {p['stats_updated']} : {p.get('impressions') or 0} impressions · {p.get('engagements') or 0} interactions · {p.get('comments') or 0} commentaires.")
        if current and p['body'].strip():
            with st.expander('Publier sur LinkedIn'):
                if not li_auth: st.caption('Reliez votre compte dans l’onglet Mon compte LinkedIn pour publier ce texte directement.')
                else:
                    st.caption(f"Publication en texte seul sur le profil de {li_auth.get('name') or 'votre compte'}. Ajoutez la photo depuis LinkedIn si besoin.")
                    sure=st.checkbox('Je confirme publier maintenant ce texte, tel qu’enregistré, sur mon profil LinkedIn',key='confirm-'+p['id'])
                    if st.button('Publier sur LinkedIn',type='primary',disabled=not sure,key='publish-'+p['id']):
                        try:
                            url=li.publish(li_auth['access_token'],li_auth['sub'],p['body'])
                            db.save(dict(p,status='Publié',published_url=url or p['published_url'],date=TODAY.isoformat()))
                            st.session_state['notice']='Publié sur LinkedIn.';goto('Publications',p['id'])
                        except RuntimeError as e: st.error(str(e))
        st.caption('Les modifications enregistrées ici restent dans le studio, sauf si vous utilisez « Publier sur LinkedIn ».')

elif page=='Assistant LinkedIn':
    st.write('Vos 11 skills LinkedIn, intégrés au studio. Le rédacteur guidé et la vérification fonctionnent seuls, sans compte ni connexion. L’IA améliore ensuite la rédaction en respectant les règles du studio. Vous publiez toujours vous-même.')
    skills=ai.available()
    voice_text=db.voice()
    repos=(db.get_meta('github') or {}).get('repos',[])
    pool={}
    for p in all_posts: pool['post:'+p['id']]=('Publication · '+p['title'],f"Publication {p['id']} ({p.get('date') or 'non planifiée'}, {p['status']}) : {p['title']}\n{p['body']}")
    for i in ideas: pool['idea:'+i['id']]=('Idée · '+i['title'],f"Idée : {i['title']}\n{i['note']}")
    for c in contents: pool['content:'+c['id']]=(content_label[c['id']],f"{c['kind']} : {c['title']} ({c['author']}) {c.get('url','')}\nCe que j’en retiens : {c['takeaways']}\n{c['quote']}")
    for r in repos: pool['repo:'+r['name']]=('GitHub · '+r['name'],f"Dépôt GitHub {r['name']} ({r['url']}) : {r['description']}\n{r['readme'][:3000]}")

    def studio_context(skill,attached):
        # Le journal remplace log.md ; les statistiques nourrissent li-audit, li-plan et li-post
        log=[f"- {p.get('date') or '?'} · {p['status']} · {p['title']} · « {p['body'].splitlines()[0] if p['body'] else ''} »" for p in all_posts if p['status'] in ('Publié','Prêt','Texte prêt')]
        stats=[f"- {r.get('title') or r['id']} · {r.get('date','')} · {r.get('impressions')} impressions · {r.get('engagements')} interactions · {r.get('comments')} commentaires" for r in li_stats]
        text=f"Date du jour : {TODAY.isoformat()} (Europe/Paris).\n\n## Journal des publications (tient lieu de log.md)\n"+'\n'.join(log)
        if skill in ('li-audit','li-plan','li-post'): text+='\n\n## Statistiques LinkedIn importées\n'+('\n'.join(stats) or 'Aucune.')
        if skill=='li-plan': text+='\n\n## Idées en attente\n'+'\n'.join(f"- {i['title']} ({db.PILLARS[i['pillar']]})" for i in ideas if i['status'] in db.IDEA_STATUSES[:3])
        prof='\n'.join(f'- {label} : {", ".join(v) if isinstance(v,list) else v}' for label,v in [('Nom',profile.get('name')),('Métiers',profile.get('metiers')),('Centres d’intérêt',profile.get('interests')),('Compétences professionnelles',profile.get('skills_pro')),('Compétences personnelles',profile.get('skills_perso')),('Présentation',profile.get('presentation')),('Résultats attendus',profile.get('objectives')),('Public visé',profile.get('audience')),('Piliers',list(db.PILLARS.values()))] if v)
        text+='\n\n## Profil (onglet Personnalisation)\n'+(prof or 'Non renseigné.')
        if attached: text+='\n\n## Éléments joints par l’utilisateur\n\n'+'\n\n'.join(pool[k][1] for k in attached)
        return text

    def save_buttons(text,key,origin):
        a,c=st.columns(2)
        if a.button('Garder comme idée',key='keep-'+key):
            db.save_item('ideas',db.new_idea(text.splitlines()[0][:90],text,source=origin))
            st.session_state['notice']='Idée enregistrée dans Idées de posts.';st.rerun()
        if c.button('Créer une publication',key='post-'+key,type='primary'):
            draft=db.new_post(text.splitlines()[0][:90],text);draft['notes']='Rédigé avec l’assistant ('+origin+').'
            st.session_state['draft']=draft;goto('Nouvelle publication')

    def chat_ui(engine,run,ready,hint=''):
        """Conversation avec un skill ; run(skill, messages, contexte) renvoie le texte au fil de l’eau."""
        c1,c2=st.columns([1,2])
        skill=c1.selectbox('Skill',skills,format_func=lambda k:ai.CATALOG[k][0]+' · '+k,key='skill-'+engine)
        c2.info(ai.CATALOG[skill][1])
        attached=st.multiselect('Joindre des éléments du studio',list(pool),format_func=lambda k:pool[k][0],key='att-'+engine)
        chats=st.session_state.setdefault('chats',{}); chat=chats.setdefault(engine+':'+skill,[])
        if chat and st.button('Nouvelle conversation',key='reset-'+engine): chats[engine+':'+skill]=[];st.rerun()
        for n,m in enumerate(chat):
            with st.chat_message(m['role']):
                st.markdown(m['content'])
                if m['role']=='assistant':
                    for b,(label,text) in enumerate(ai.blocks(m['content'])):
                        with st.container(border=True):
                            try: score=human_score(text); st.caption(f"{label} · {len(text)} caractères · score humain {score['human_score']:.0f}/100 ({score['verdict']}) · détecteur li-human local")
                            except RuntimeError: st.caption(f'{label} · {len(text)} caractères')
                            save_buttons(text,f'{engine}-{skill}-{n}-{b}',engine+' · '+skill)
        prompt=st.chat_input(ai.CATALOG[skill][2],key='input-'+engine)
        if prompt and not ready: st.error(hint)
        elif prompt:
            chat.append(dict(role='user',content=prompt))
            with st.chat_message('user'): st.markdown(prompt)
            with st.chat_message('assistant'):
                try:
                    answer=st.write_stream(run(skill,[dict(role=m['role'],content=m['content']) for m in chat],studio_context(skill,attached)))
                    chat.append(dict(role='assistant',content=answer));st.rerun()
                except Exception as e:
                    chat.pop();st.error(ai.explain(e))

    with st.expander('Connexion à l’IA (Claude)',expanded=not (ai.key_from_env() or st.session_state.get('anthropic_key'))):
        if not ai.has_sdk(): st.warning('Installez le paquet anthropic (pip install -r requirements.txt) pour connecter l’IA.')
        c1,c2=st.columns(2)
        if ai.key_from_env(): c1.success('Clé API trouvée dans l’environnement.')
        else: st.session_state['anthropic_key']=c1.text_input('Clé API Anthropic',st.session_state.get('anthropic_key',''),type='password',help='platform.claude.com → API Keys. Gardée en mémoire le temps de la session, jamais enregistrée. Pour ne plus la saisir, lancez le studio avec la variable ANTHROPIC_API_KEY.')
        model=c2.selectbox('Modèle',list(ai.MODELS),format_func=ai.MODELS.get,key='ai-model')
        st.caption('Chaque appel est facturé sur votre compte API Anthropic. Le rédacteur guidé et la vérification restent gratuits et fonctionnent sans connexion.')
    api_key=st.session_state.get('anthropic_key') or None
    ready=ai.has_sdk() and (ai.key_from_env() or bool(api_key))
    NO_KEY='Ajoutez votre clé API Anthropic dans « Connexion à l’IA » en haut de la page.'
    t_guide,t_chat,t_check,t_voice=st.tabs(['✍️ Rédacteur guidé','💬 Conversation IA','🔎 Vérifier un texte','🗣️ Profil de voix'])

    with t_guide:
        st.caption('Donnez la matière : le studio propose les accroches adaptées parmi les 21 formules de li-post, assemble le post dans la bonne structure, puis le nettoie et le note avec li-human. Rien n’est inventé : chaque phrase vient de vos réponses.')
        starts={'':'Partir d’une page blanche'}
        for i in ideas: starts['idea:'+i['id']]='Idée · '+i['title']
        for c in contents: starts['content:'+c['id']]=content_label[c['id']]
        for r in repos: starts['repo:'+r['name']]='GitHub · '+r['name']
        for n,pf in enumerate(rd.proofs(voice_text)): starts[f'proof:{n}']='Preuve · '+pf[:80]
        c1,c2=st.columns([4,1])
        start=c1.selectbox('Partir de…',list(starts),format_func=starts.get)
        if c2.button('Pré-remplir',disabled=not start):
            kind,ref=start.split(':',1); fill={}
            if kind=='idea':
                i=next(x for x in ideas if x['id']==ref); fill=dict(fait=i['note'][:400])
            elif kind=='content':
                c=next(x for x in contents if x['id']==ref)
                verb={'Podcast':'En écoutant','Vidéo':'En regardant','Conférence':'En assistant à'}.get(c['kind'],'En lisant')
                fill=dict(contexte=f"{verb} « {c['title']} »"+(f" ({c['author']})" if c['author'] else ''),fait=c['takeaways'],citation=c['quote'])
            elif kind=='repo':
                r=next(x for x in repos if x['name']==ref); _,_,res=db.repo_insights(r,research['opportunites'])
                fill=dict(contexte=f"Dans mon projet {r['name'].replace('-',' ')}",fait='La question posée : '+_low_first(r['description'].rstrip('. '))+'.',chiffre=res[0] if res else '',points='\n'.join(res[1:4]))
            else:
                fill=dict(chiffre=rd.proofs(voice_text)[int(ref)])
            for k in list(rd.FIELDS)+list(rd.EXTRA): st.session_state['rd-'+k]=fill.get(k,'')
            st.rerun()
        data={}
        for k,(label,help_) in rd.FIELDS.items():
            widget=st.text_area if k in ('fait','points') else st.text_input
            data[k]=widget(label,key='rd-'+k,placeholder=help_)
        with st.expander('Ingrédients pour d’autres accroches (contre-pied, avant/après, erreur, citation…)'):
            cols=st.columns(2)
            for n,(k,(label,help_)) in enumerate(rd.EXTRA.items()): data[k]=cols[n%2].text_input(label,key='rd-'+k,placeholder=help_)
        if not data['fait'].strip():
            st.info('Commencez par « Ce qui s’est passé » : un post a besoin d’un fait précis et vrai.')
        else:
            options=rd.hooks(data)
            if not options: st.warning('Ajoutez un chiffre, un contexte ou un ingrédient d’accroche pour débloquer des formules.')
            else:
                choice=st.radio('Choisissez l’accroche',range(len(options[:6])),format_func=lambda n:f"#{options[n]['id']} {options[n]['name']} · {options[n]['text']}")
                hook=options[choice]; st.caption(f"Pour : {hook['best_for']} Piège : {hook['trap']}")
                raw=rd.compose(data,hook)
                try:
                    clean=ai.humanize(raw); score=ai.detect(clean['text'])
                    final=clean['text']; changes=sum(x['count'] for part in ('invisible','typographic','lexical') for x in clean['report'][part])
                except RuntimeError: final,score,changes,clean=raw,None,0,None
                text=st.text_area('Votre post, modifiable avant de le garder',final,height=360,key='rd-final-'+str(hash(final)))
                c1,c2,c3=st.columns(3)
                c1.metric('Caractères',len(text))
                if score: c2.metric('Score humain (li-human)',f"{score['human_score']:.0f}/100",score['verdict'],delta_color='off'); c3.metric('Corrections automatiques',changes)
                for level,msg in rd.checks(text,data): (st.caption if level=='ok' else st.warning)(('✓ ' if level=='ok' else '')+msg)
                for f in (clean or {}).get('report',{}).get('structures',[]): st.warning(f"{f['name']} : {f['fix']}")
                save_buttons(text,'guide','rédacteur guidé')
                st.subheader('Améliorer avec l’IA')
                st.caption('L’IA réécrit ce brouillon avec les skills li-post et li-human, en gardant vos faits, vos chiffres et l’accroche choisie. La version obtenue repasse ensuite par les mêmes contrôles du studio.')
                ai_key='rd-ai-'+str(hash(text))
                if st.button('✨ Améliorer la rédaction',type='primary',disabled=not ready,help=None if ready else NO_KEY):
                    try:
                        st.session_state[ai_key]=st.write_stream(ai.stream('li-post',[dict(role='user',content=ai.improve_request(text,data,hook))],studio_context('li-post',[]),model,api_key))
                        st.rerun()
                    except Exception as e: st.error(ai.explain(e))
                if not ready: st.caption(NO_KEY)
                if st.session_state.get(ai_key):
                    answer=st.session_state[ai_key]
                    for b,(label,version) in enumerate(ai.blocks(answer)):
                        with st.container(border=True):
                            st.markdown(f'**Version améliorée · {label}**')
                            st.code(version,language=None,wrap_lines=True)
                            try: st.caption(f"{len(version)} caractères · score humain {human_score(version)['human_score']:.0f}/100 ({human_score(version)['verdict']})")
                            except RuntimeError: pass
                            if label!='EN':
                                for level,msg in rd.checks(version,data): (st.caption if level=='ok' else st.warning)(('✓ ' if level=='ok' else '')+msg)
                            save_buttons(version,f'guide-ai-{b}','rédacteur guidé + IA')
                    notes=re.sub(r'```.*?```','',answer,flags=re.S).strip()
                    if notes:
                        with st.expander('Ce que l’IA a modifié'): st.markdown(notes)

    with t_chat:
        st.caption('Discutez avec n’importe lequel des 11 skills : posts, carrousel, plan de la semaine, analyse de vos résultats, profil, commentaires, messages.')
        chat_ui('claude',lambda skill,msgs,ctx:ai.stream(skill,msgs,ctx,model,api_key),ready,NO_KEY)

    with t_check:
        st.caption('Le skill li-human, exécuté sur cet ordinateur : retire les marques d’IA et note le texte sur cinq critères.')
        draft=st.text_area('Texte à vérifier',key='human-text',height=180)
        if st.button('Nettoyer et noter',disabled=not draft.strip()):
            try:
                clean=ai.humanize(draft); before,after=ai.detect(draft),ai.detect(clean['text'])
                c1,c2=st.columns(2)
                c1.metric('Score humain avant',f"{before['human_score']:.0f}/100",before['verdict'],delta_color='off'); c2.metric('Après nettoyage',f"{after['human_score']:.0f}/100",after['verdict'],delta_color='off')
                st.code(clean['text'],language=None,wrap_lines=True)
                for k,v in after['checks'].items(): st.caption(f"{k} · {v['score']:.0f} · {v['detail']}")
                for f in clean['report']['structures']: st.warning(f"{f['name']} ({f['count']}) : {f['fix']}")
            except RuntimeError as e: st.error(str(e))

    with t_voice:
        voice=st.text_area('Profil de voix (voice.md) : qui vous êtes, vos mots, vos preuves. Tous les moteurs s’en servent.',voice_text,height=360)
        b1,b2=st.columns(2)
        if b1.button('Enregistrer le profil de voix'):
            db.save_voice(voice);st.session_state['notice']='Profil de voix enregistré.';st.rerun()
        if ai.SOURCE.exists() and b2.button('Mettre à jour les skills depuis Claude'):
            st.session_state['notice']='Skills mis à jour : '+', '.join(ai.sync_skills());st.rerun()
        st.caption('Skills issus de github.com/Jakeschincariol/linkedin-agent-skill (licence MIT, voir skills/LICENSE).')

elif page=='Idées de posts':
    st.write('Notez une idée dès qu’elle arrive, même en vrac. Elle reste un brouillon jusqu’à ce que vous la transformiez en publication.')
    with st.form('quick-idea',clear_on_submit=True):
        c1,c2=st.columns([3,1])
        title=c1.text_input('Mon idée en une phrase')
        pillar=c2.selectbox('Pilier',list(db.PILLARS),format_func=lambda x:db.PILLARS[x])
        note=st.text_area('Notes en vrac : anecdote, chiffre, question, angle…',height=120)
        c1,c2=st.columns(2)
        content=c1.selectbox('Contenu qui l’inspire',['']+list(content_label),format_func=lambda x:content_label.get(x,'Aucun'))
        url=c2.text_input('Lien utile')
        if st.form_submit_button('Noter l’idée',type='primary'):
            try:
                db.save_item('ideas',db.new_idea(title,note,pillar,url=url.strip(),content_id=content,source=content_label.get(content,'').strip()))
                st.session_state['notice']='Idée notée.';st.rerun()
            except ValueError as e: st.error(str(e))
    c1,c2=st.columns([2,1])
    shown=c1.multiselect('Statuts affichés',db.IDEA_STATUSES,default=db.IDEA_STATUSES[:3])
    q=c2.text_input('Rechercher',key='idea-q')
    chosen=[i for i in ideas if i['status'] in shown and q.casefold() in (i['title']+' '+i['note']+' '+i.get('tags','')).casefold()]
    st.caption(f'{len(chosen)} idée(s) affichée(s) sur {len(ideas)}')
    if not ideas: st.info('Aucune idée pour l’instant. Les onglets GitHub et Contenus consommés peuvent aussi en créer.')
    for idea in chosen:
        with st.expander(f"{idea['title']} · {idea['status']} · {db.PILLARS[idea['pillar']]}"):
            if idea.get('source') or idea.get('repo'): st.caption('Inspirée de : '+(idea.get('source') or idea['repo']))
            with st.form('idea-'+idea['id']):
                title=st.text_input('Idée',idea['title'])
                c1,c2,c3=st.columns(3)
                status=c1.selectbox('Statut',db.IDEA_STATUSES,index=db.IDEA_STATUSES.index(idea['status']))
                pillar=c2.selectbox('Pilier',list(db.PILLARS),format_func=lambda x:db.PILLARS[x],index=list(db.PILLARS).index(idea['pillar']))
                tag=c3.text_input('Mots-clés, séparés par des virgules',idea.get('tags',''))
                note=st.text_area('Brouillon à retravailler',idea['note'],height=220)
                url=st.text_input('Lien utile',idea.get('url',''))
                if st.form_submit_button('Enregistrer'):
                    try: db.save_item('ideas',dict(idea,title=title,status=status,pillar=pillar,tags=tag,note=note,url=url.strip()));st.session_state['notice']='Idée enregistrée.';st.rerun()
                    except ValueError as e: st.error(str(e))
            post=next((p for p in all_posts if p['id']==idea.get('post_id')),None)
            c1,c2=st.columns(2)
            if post: c1.markdown('Publication liée : '+post_link(post),unsafe_allow_html=True)
            elif c1.button('Transformer en publication',key='to-post-'+idea['id'],type='primary'): idea_to_post(idea)
            if c2.button('Supprimer cette idée',key='del-'+idea['id']):
                db.delete_item('ideas',idea['id']);st.session_state['notice']='Idée supprimée.';st.rerun()

elif page=='Contenus consommés':
    st.write('Podcasts, lectures, vidéos… Gardez ce que vous en retenez pour y puiser des idées de posts, avec la source à citer.')
    fresh=next((c for c in contents if c['id']==st.session_state.get('just_added')),None)
    if fresh:
        with st.container(border=True):
            st.markdown(f"**Vient d’arriver :** {ICONS.get(fresh['kind'],'')} {escape(fresh['title'])}"+(f" · {escape(fresh['author'])}" if fresh['author'] else ''))
            with st.form('fresh-'+fresh['id']):
                c1,c2=st.columns([1,3])
                kind=c1.selectbox('Type',db.CONTENT_TYPES,index=db.CONTENT_TYPES.index(fresh['kind']))
                title=c2.text_input('Titre',fresh['title'])
                takeaways=st.text_area('Ce que j’en retiens (facultatif, à compléter plus tard)',fresh['takeaways'])
                if st.form_submit_button('Enregistrer',type='primary'):
                    db.save_item('contents',dict(fresh,kind=kind,title=title,takeaways=takeaways,tags='' if takeaways else fresh.get('tags','')))
                    st.session_state.pop('just_added',None);st.session_state['notice']='Contenu enregistré.';st.rerun()
    with st.expander('Ajouter depuis un lien'):
        st.caption('Sur iPhone, le raccourci « Ajouter au studio » fait la même chose depuis le bouton Partager de Podcasts, Spotify ou YouTube (voir MISE-EN-LIGNE.md).')
        link=st.text_input('Collez un lien YouTube, Spotify, Apple Podcasts ou d’article',key='link-add')
        if st.button('Ajouter ce lien',disabled=not link.strip()):
            try:
                item,known=db.add_shared_link(link)
                st.session_state['notice']=('Déjà dans vos contenus : ' if known else 'Ajouté : ')+item['title'];st.session_state['just_added']=item['id'];st.rerun()
            except ValueError as e: st.error(str(e))
    with st.expander('Ajouter un contenu',expanded=not contents):
        with st.form('new-content',clear_on_submit=True):
            c1,c2,c3=st.columns([1,2,1])
            kind=c1.selectbox('Type',db.CONTENT_TYPES,format_func=lambda x:ICONS[x]+' '+x)
            title=c2.text_input('Titre')
            author=c3.text_input('Auteur, invité ou émission')
            c1,c2,c3=st.columns([2,1,1])
            url=c1.text_input('Lien')
            day=c2.date_input('Consommé le',TODAY)
            pillar=c3.selectbox('Pilier',list(db.PILLARS),format_func=lambda x:db.PILLARS[x])
            takeaways=st.text_area('Ce que j’en retiens')
            quote=st.text_input('Idée ou citation clé (courte, avec la source)')
            tag=st.text_input('Mots-clés, séparés par des virgules')
            if st.form_submit_button('Ajouter',type='primary'):
                try:
                    db.save_item('contents',dict(db.new_content(kind),title=title,author=author,url=url.strip(),date=day.isoformat(),pillar=pillar,takeaways=takeaways,quote=quote,tags=tag))
                    st.session_state['notice']='Contenu ajouté.';st.rerun()
                except ValueError as e: st.error(str(e))
    c1,c2=st.columns([2,1])
    kinds=c1.multiselect('Types',db.CONTENT_TYPES,default=db.CONTENT_TYPES,format_func=lambda x:ICONS[x]+' '+x)
    q=c2.text_input('Rechercher',key='content-q')
    chosen=[c for c in contents if c['kind'] in kinds and q.casefold() in json.dumps(c,ensure_ascii=False).casefold()]
    st.caption(f'{len(chosen)} contenu(s) affiché(s) sur {len(contents)}')
    for c in chosen:
        used=[i for i in ideas if i.get('content_id')==c['id']]
        with st.container(border=True):
            st.markdown(f"**{ICONS.get(c['kind'],'')} {escape(c['title'])}** · {escape(c['author'])}"+(f" · [ouvrir]({db.md_url(c['url'])})" if c.get('url') else ''))
            st.caption(f"{c['kind']} · {c.get('date') or 'date à compléter'} · {db.PILLARS[c['pillar']]} · {len(used)} idée(s) tirée(s)")
            if c['takeaways']: st.write(c['takeaways'])
            if c['quote']: st.markdown('> '+c['quote'])
            if c.get('tags'): st.markdown(tags(c['tags']),unsafe_allow_html=True)
            b1,b2,b3=st.columns(3)
            if b1.button('Créer une idée de post',key='idea-from-'+c['id'],type='primary'):
                note=f"Contenu : {c['title']} ({c['author']})\nCe que j’en retiens : {c['takeaways']}\n"+(f"Citation : {c['quote']}\n" if c['quote'] else '')+'Mon angle : ce que j’en fais dans mon parcours ou mes projets…'
                db.save_item('ideas',db.new_idea('À partir de « '+c['title']+' »',note,c['pillar'],source=content_label[c['id']].strip(),url=c.get('url',''),content_id=c['id']))
                st.session_state['notice']='Idée créée dans l’onglet Idées de posts.';st.rerun()
            with b2.popover('Modifier'):
                with st.form('content-'+c['id']):
                    kind=st.selectbox('Type',db.CONTENT_TYPES,index=db.CONTENT_TYPES.index(c['kind']))
                    title=st.text_input('Titre',c['title']); author=st.text_input('Auteur, invité ou émission',c['author'])
                    url=st.text_input('Lien',c.get('url','')); day=st.text_input('Date (AAAA-MM-JJ)',c.get('date',''))
                    takeaways=st.text_area('Ce que j’en retiens',c['takeaways']); quote=st.text_input('Idée ou citation clé',c['quote'])
                    tag=st.text_input('Mots-clés',c.get('tags',''))
                    pillar=st.selectbox('Pilier',list(db.PILLARS),format_func=lambda x:db.PILLARS[x],index=list(db.PILLARS).index(c['pillar']))
                    if st.form_submit_button('Enregistrer'):
                        try:
                            if day: date.fromisoformat(day)
                            db.save_item('contents',dict(c,kind=kind,title=title,author=author,url=url.strip(),date=day,takeaways=takeaways,quote=quote,tags=tag,pillar=pillar));st.session_state['notice']='Contenu enregistré.';st.rerun()
                        except ValueError as e: st.error(str(e) if 'Donnez' in str(e) or 'lien' in str(e) else 'Date attendue au format AAAA-MM-JJ.')
            if b3.button('Supprimer',key='del-c-'+c['id']):
                db.delete_item('contents',c['id']);st.session_state['notice']='Contenu supprimé.';st.rerun()

elif page=='GitHub':
    cache=db.get_meta('github')
    st.write('Vos dépôts deviennent une réserve de preuves : ce que vous avez réalisé, rapproché des piliers et des sujets recommandés.')
    with st.form('github-sync'):
        c1,c2=st.columns(2)
        user=c1.text_input('Identifiant GitHub',(cache or {}).get('user') or profile.get('github_user',''))
        token=c2.text_input('Jeton GitHub (facultatif)',type='password',help='Utile pour inclure vos dépôts privés et ceux de vos organisations. Il n’est pas enregistré : il reste le temps de cette session.')
        if st.form_submit_button('Synchroniser GitHub',type='primary'):
            try:
                with st.spinner('Lecture des dépôts…'): cache=db.github_sync(user.strip(),token.strip() or None)
                st.session_state['notice']=f"{len(cache['repos'])} dépôts synchronisés.";st.rerun()
            except ValueError as e: st.error(str(e))
    if not cache: st.info('Lancez une première synchronisation.')
    else:
        st.caption(f"Dernière synchronisation : {cache['fetched_at'].replace('T',' à ')} · {len(cache['repos'])} dépôts · github.com/{cache['user']}")
        for repo in cache['repos']:
            pillars,topics,results=db.repo_insights(repo,research['opportunites'])
            linked=[i for i in ideas if i.get('repo')==repo['full_name']]
            with st.container(border=True):
                st.markdown(f"**[{escape(repo['name'])}]({db.md_url(repo['url'])})**"+(' · privé' if repo['private'] else ''))
                st.caption(' · '.join(x for x in [repo['language'],'mis à jour le '+repo['pushed_at'],' / '.join(db.PILLARS[k] for k in pillars),f'{len(linked)} idée(s) notée(s)'] if x))
                if repo['description']: st.write(repo['description'])
                if results:
                    st.markdown('**Ce que vous avez réalisé**')
                    for r in results: st.markdown('- '+r)
                if topics: st.markdown('**Sujets recommandés liés :** '+' · '.join(t[0] for t in topics))
                short=repo['name'].replace('-',' ')
                for k in pillars:
                    angle=ANGLES[k].format(n=short)
                    a,b=st.columns([4,1])
                    a.write('✦ '+angle)
                    if b.button('Noter l’idée',key=f"gh-{repo['name']}-{k}"):
                        note=f"Projet : {repo['description']}\n"+''.join('- '+r+'\n' for r in results)+(f"Sujet recommandé lié : {topics[0][0]} ({topics[0][1]})\n" if topics else '')+'Ma contribution précise, la décision prise, ce que je ferais autrement…'
                        db.save_item('ideas',db.new_idea(angle,note,k,source='GitHub · '+repo['name'],url=repo['url'],repo=repo['full_name']))
                        st.session_state['notice']='Idée ajoutée dans l’onglet Idées de posts.';st.rerun()
                if repo['readme']:
                    with st.expander('Lire le README'): st.markdown(repo['readme'][:4000])

elif page=='Impact LinkedIn':
    st.write('LinkedIn ne permet pas à une application personnelle de lire les statistiques de vos posts sans validation de partenariat. Le studio importe donc l’export officiel, en un clic, et rattache chaque chiffre à la bonne publication grâce à son lien.')
    with st.expander('Comment récupérer l’export (1 minute)',expanded=not any(r.get('source','').endswith(('.xlsx','.csv')) for r in li_stats)):
        st.markdown('1. Sur LinkedIn, ouvrez votre profil → **Statistiques** → **Impressions des posts**.\n2. Choisissez la période (365 jours pour tout récupérer) puis **Exporter**.\n3. Déposez le fichier ci-dessous. Pour un post précis : ses statistiques → **Exporter**.\n4. Dans **Publications**, collez le lien de chaque post publié : ses chiffres s’y affichent automatiquement.')
    upload=st.file_uploader('Export LinkedIn (XLSX ou CSV)',type=['xlsx','csv'])
    if upload and st.button('Importer les statistiques',type='primary'):
        try:
            n,d,m=db.import_linkedin(upload.getvalue(),upload.name)
            st.session_state['notice']=f'{n} publication(s) et {d} journée(s) importées · {m} rattachée(s) à vos fiches.';st.rerun()
        except ValueError as e: st.error(str(e))
    imp=sum(r.get('impressions') or 0 for r in li_stats); eng=sum(r.get('engagements') or 0 for r in li_stats)
    cols=st.columns(4)
    cols[0].metric('Posts suivis',len(li_stats)); cols[1].metric('Impressions',f'{imp:,}'.replace(',',' '))
    cols[2].metric('Interactions',eng); cols[3].metric('Taux d’engagement',f'{100*eng/imp:.2f} %'.replace('.',',') if imp else '–')
    st.caption('Taux = interactions (réactions + commentaires + republications) ÷ impressions, comme dans l’audit.')
    if li_stats:
        import pandas as pd
        by_activity={db.activity_id(p.get('published_url')):p for p in all_posts if p.get('published_url')}
        df=pd.DataFrame([dict(id=r['id'],Titre=r.get('title') or (by_activity.get(r['id']) or {}).get('title',''),Date=r.get('date',''),Impressions=r.get('impressions'),Interactions=r.get('engagements'),Commentaires=r.get('comments'),Taux=round(100*(r.get('engagements') or 0)/r['impressions'],2) if r.get('impressions') else None,Relevé=r.get('collected',''),Lien=r.get('url','')) for r in li_stats]).sort_values('Impressions',ascending=False,na_position='last')
        edited=st.data_editor(df,hide_index=True,width='stretch',disabled=[c for c in df.columns if c!='Titre'],column_config={'id':None,'Lien':st.column_config.LinkColumn('Post',display_text='ouvrir'),'Taux':st.column_config.NumberColumn('Taux %',format='%.2f')})
        if st.button('Enregistrer les titres'):
            known={r['id']:r for r in li_stats}
            for _,row in edited.iterrows():
                if row['Titre']!=known[row['id']].get('title',''): db.save_item('linkedin',dict(known[row['id']],title=row['Titre']))
            st.session_state['notice']='Titres enregistrés.';st.rerun()
    daily=db.get_meta('linkedin_daily',{})
    if daily:
        import pandas as pd
        st.subheader('Évolution quotidienne')
        series=pd.DataFrame.from_dict(daily,orient='index').sort_index()
        series=series[[c for c in ['impressions','engagements'] if c in series]]
        st.line_chart(series,color=['#6B4A33','#1C1A17'][:len(series.columns)])
    waiting=[p for p in all_posts if p['status']=='Publié' and not p.get('stats_updated')]
    if waiting:
        st.subheader('Publiés, en attente de statistiques')
        for p in waiting: st.markdown(post_link(p)+(' · lien LinkedIn à ajouter' if not p.get('published_url') else ''),unsafe_allow_html=True)

elif page=='Personnalisation':
    st.write('Présentez-vous. Le studio et l’IA s’en servent pour adapter les idées, les posts et les analyses à votre profil.')
    with st.form('profile'):
        name=st.text_input('Prénom et nom',profile.get('name',''))
        def tags_input(key,label,help_):
            current=profile.get(key,[])
            return st.multiselect(label,sorted(set(SUGGESTIONS[key]+current)),default=current,accept_new_options=True,placeholder='Choisissez ou tapez puis Entrée',help=help_)
        metiers=tags_input('metiers','Métier(s)','Vous pouvez en ajouter plusieurs : actuel, visé, en reconversion…')
        interests=tags_input('interests','Centres d’intérêt','Ce qui vous anime, au travail comme en dehors.')
        c1,c2=st.columns(2)
        with c1: skills_pro=tags_input('skills_pro','Compétences professionnelles','Savoir-faire, méthodes, outils.')
        with c2: skills_perso=tags_input('skills_perso','Compétences personnelles','Savoir-être, qualités.')
        presentation=st.text_area('Présentation : qui vous êtes, ce que vous faites, ce que vous visez',profile.get('presentation',''),max_chars=800,height=130,placeholder='En trois ou quatre phrases.')
        objectives=st.text_area('Résultats attendus : ce que LinkedIn doit vous apporter',profile.get('objectives',''),height=100,placeholder='Ex. : décrocher une alternance d’ici mars, cinq échanges qualifiés par mois, être identifiée sur un sujet.')
        audience=st.text_input('Pour qui vous écrivez',profile.get('audience',''),placeholder='Ex. : recruteurs et responsables produit de startups')
        st.markdown('**Vos cinq piliers éditoriaux** : les grands thèmes de vos posts.')
        cols=st.columns(5); pillars={}
        for col,(k,default) in zip(cols,db.DEFAULT_PILLARS.items()): pillars[k]=col.text_input(f'Pilier {k}',db.PILLARS[k],placeholder=default)
        c1,c2=st.columns(2)
        linkedin_url=c1.text_input('Adresse de votre profil LinkedIn',profile.get('linkedin_url',''),placeholder='https://www.linkedin.com/in/…')
        github_user=c2.text_input('Identifiant GitHub (facultatif)',profile.get('github_user',''))
        if st.form_submit_button('Enregistrer mon profil',type='primary'):
            if linkedin_url and not linkedin_url.startswith('https://'): st.error('L’adresse LinkedIn doit commencer par https://.')
            else:
                db.save_profile(dict(profile,name=name.strip(),metiers=metiers,interests=interests,skills_pro=skills_pro,skills_perso=skills_perso,presentation=presentation.strip(),objectives=objectives.strip(),audience=audience.strip(),pillars=pillars,linkedin_url=linkedin_url.strip(),github_user=github_user.strip()))
                st.session_state['notice']='Profil enregistré.';st.rerun()
    if profile.get('name'):
        with st.container(border=True):
            st.markdown(f"### {escape(profile['name'])}")
            if profile.get('metiers'): st.markdown(tags(', '.join(profile['metiers'])),unsafe_allow_html=True)
            if profile.get('presentation'): st.write(profile['presentation'])
            if profile.get('objectives'): st.caption('Objectifs : '+profile['objectives'])

elif page=='Mon compte LinkedIn':
    st.write('Reliez votre compte pour publier depuis le studio, puis importez vos statistiques pour suivre l’impact de vos posts.')
    c1,c2=st.columns(2)
    with c1, st.container(border=True):
        st.markdown('**1. Connexion du compte**')
        if not li.configured():
            st.caption('La connexion demande une application LinkedIn gratuite, créée une fois pour votre studio.')
            with st.expander('Créer l’application LinkedIn (10 minutes)'):
                st.markdown(f"""1. Sur [developer.linkedin.com](https://www.linkedin.com/developers/apps), **Create app** : un nom, votre **page LinkedIn** (LinkedIn en exige une ; créez une page vitrine si besoin), un logo.
2. Onglet **Products** : demandez **Sign In with LinkedIn using OpenID Connect** et **Share on LinkedIn** (accès immédiat).
3. Onglet **Auth** : dans *Authorized redirect URLs*, ajoutez `{li.redirect_uri()}` (l’adresse de votre studio).
4. Copiez **Client ID** et **Primary Client Secret** dans les secrets du studio :

```toml
LINKEDIN_CLIENT_ID = "…"
LINKEDIN_CLIENT_SECRET = "…"
APP_URL = "{li.redirect_uri().rstrip('/')}"
```
5. Redémarrez le studio : le bouton de connexion apparaît ici.""")
        elif not li_auth:
            st.caption('Vous serez redirigé vers LinkedIn pour autoriser le studio à lire votre nom et votre photo, et à publier en votre nom quand vous le demandez.')
            import secrets
            state=st.session_state.setdefault('li_state',secrets.token_urlsafe(16))
            if db.get_meta('linkedin_state')!=state: db.set_meta('linkedin_state',state)
            st.link_button('Se connecter avec LinkedIn',li.auth_url(state),type='primary')
        else:
            a,b=st.columns([1,3])
            if li_auth.get('picture'): a.image(li_auth['picture'],width=72)
            b.markdown(f"**{escape(li_auth.get('name',''))}**  \n{escape(li_auth.get('email',''))}")
            b.caption(f"Connexion valable jusqu’au {li_auth.get('expires_at','?').replace('T',' à ')}. Reconnectez-vous ensuite.")
            st.success('Compte relié : le bouton « Publier sur LinkedIn » est disponible dans chaque publication.')
            if st.button('Déconnecter ce compte'):
                db.delete_meta('linkedin_auth');st.session_state['notice']='Compte LinkedIn déconnecté.';st.rerun()
    with c2, st.container(border=True):
        st.markdown('**2. Statistiques de vos posts**')
        st.caption('LinkedIn ne transmet pas les statistiques des profils personnels aux applications : elles se récupèrent avec le bouton Exporter de LinkedIn, en une minute.')
        st.metric('Posts suivis',len(li_stats))
        if st.button('Importer mes statistiques',type='primary'): goto('Impact LinkedIn')

elif page=='Benchmark international':
    fr=sum(a['id'].startswith('FR') for a in research['benchmark'])
    st.write(f"{len(research['benchmark'])} créateurs observés : {fr} en France, {len(research['benchmark'])-fr} aux États-Unis, relevé du {research.get('date','29 octobre 2026')}, centré sur le produit (PM / PO). Ce n’est pas un classement de performance : une source d’inspiration, à compléter de vos propres favoris.")
    c1,c2,c3=st.columns(3)
    region=c1.selectbox('Zone',['Tous','France','États-Unis'])
    query=c2.text_input('Nom, entreprise ou sujet')
    favorites=c3.checkbox('Mes favoris uniquement')
    matches=[]; states=db.accounts()
    for a in research['benchmark']:
        fav,notes=states.get(a['id'],(False,''))
        is_fr=a['id'].startswith('FR')
        if region=='France' and not is_fr or region=='États-Unis' and is_fr: continue
        if query.casefold() not in json.dumps(a,ensure_ascii=False).casefold(): continue
        if favorites and not fav: continue
        matches.append(a)
    st.caption(f'{len(matches)} comptes affichés')
    for a in matches:
        fav,notes=states.get(a['id'],(False,''))
        with st.expander(('★ ' if fav else '')+a['nom']+' · '+a['pays']):
            st.write(a['fonction']+' · '+a['entreprise'])
            st.markdown('**Sujets :** '+a['themes'])
            st.write('Formats : '+a['formats']); st.write('Style : '+a['style'])
            st.info(a['enseignement'])
            st.write('Exemple observé : '+a['exemple'])
            st.caption('Accroche : '+a['hook'])
            st.caption('Récence observée : '+a['recence']+' · '+a['frequence_observee'])
            st.caption('Interactions à la date de collecte : '+a['interactions'])
            st.caption('Audience au relevé : '+str(a.get('audience') or 'Non renseignée'))
            st.warning(a['limites'])
            links=st.columns(3)
            links[0].link_button('Profil LinkedIn',a['profil'])
            links[1].link_button('Fil des publications',a['fil'])
            if a.get('publication'): links[2].link_button('Exemple sourcé',a['publication'])
            with st.form('account-'+a['id']):
                favorite=st.checkbox('Garder en favori',fav)
                note=st.text_area('Mes observations',notes)
                if st.form_submit_button('Enregistrer mes notes'):
                    db.save_account(a['id'],favorite,note);st.success('Notes enregistrées.')
            if st.button('Créer un sujet inspiré de ce compte',key='inspire-'+a['id']):
                draft=db.new_post('Idée inspirée de '+a['nom'],sources=a['profil']);draft['notes']='Piste à traiter avec mon propre regard : '+a['enseignement']+'\nNe pas reprendre le texte du créateur.'
                st.session_state['draft']=draft;goto('Nouvelle publication')

elif page=='Sujets & stratégie':
    if profile.get('presentation'): st.write('**Positionnement :** '+profile['presentation'])
    if profile.get('objectives'): st.caption('Résultats attendus : '+profile['objectives'])
    if not profile.get('presentation'): st.info('Décrivez votre positionnement et vos objectifs dans l’onglet Personnalisation.')
    st.subheader('Vos cinq piliers')
    cols=st.columns(5)
    for col,(k,name) in zip(cols,db.PILLARS.items()):
        col.metric(name,sum(p['pillar']==k for p in all_posts),f"{sum(i['pillar']==k for i in ideas)} idée(s)",delta_color='off',help='Publications dans ce pilier, et idées en réserve')
    details={row[0]:row for row in research.get('piliers',[])}
    for k,name in db.PILLARS.items():
        if k in details:
            _,_,share,objective,audience,examples=details[k]
            with st.expander(f'{name} · {share:.0%} du calendrier initial'):
                st.write(objective);st.caption('Public : '+audience);st.write(examples)
    st.subheader('Réserve de sujets')
    if not research.get('opportunites'): st.caption('Vos pistes de sujets vivent dans l’onglet Idées de posts.')
    for i,(title,angle,origin) in enumerate(research.get('opportunites',[])):
        with st.container(border=True):
            st.markdown('**'+title+'**');st.write(angle);st.caption(origin)
            if st.button('Préparer ce sujet',key='topic-'+str(i)):
                draft=db.new_post(title);draft['notes']=angle+'\nOrigine : '+origin
                st.session_state['draft']=draft;goto('Nouvelle publication')
    if research.get('sources'):
        st.subheader('Bibliothèque de références')
        for title,url in research['sources'].values(): st.markdown(f'[{title}]({url})')

elif page=='Sauvegardes':
    st.write('Vos modifications, photos et notes sont enregistrées dans le dossier personnel de cette application. Téléchargez régulièrement une sauvegarde.')
    st.download_button('Sauvegarde complète · ZIP',db.backup(),'studio-editorial-sauvegarde.zip',mime='application/zip',type='primary')
    st.download_button('Publications · JSON',json.dumps(all_posts,ensure_ascii=False,indent=2),'publications.json',mime='application/json')
    rows=[]
    for p in all_posts:
        row={k:p.get(k,'') for k in ['id','title','date','time','platform','status','priority','body','published_url','impressions','comments','leads']}
        row={k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in row.items()};rows.append(row)
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(rows[0]) if rows else ['id','title']);writer.writeheader();writer.writerows(rows)
    st.download_button('Planning et textes · CSV',stream.getvalue().encode('utf-8-sig'),'planning.csv',mime='text/csv')
    st.caption('Le ZIP inclut un export JSON, les photos, le benchmark et une sauvegarde SQL des publications, favoris et notes. Les données sources initiales sont conservées séparément.')
