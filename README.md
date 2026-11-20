# Studio éditorial LinkedIn

Un outil personnel pour planifier, écrire et analyser ses publications LinkedIn : calendrier, idées, contenus consommés, rédaction guidée avec 21 formules d’accroche, assistant IA, statistiques et publication directe sur votre profil.

Conçu par [Manon Desclaux](https://github.com/manondesclaux) pour son propre usage, puis ouvert à tous. L’outil démarre vide : vos données restent dans votre propre base, sur votre ordinateur ou dans votre compte Supabase.

## Ce que fait le studio

| Onglet | À quoi il sert |
|---|---|
| **Personnalisation** | Votre profil : métiers (plusieurs possibles), centres d’intérêt, compétences professionnelles et personnelles, présentation, résultats attendus, public visé et vos cinq piliers éditoriaux. L’assistant s’en sert pour adapter les posts. |
| **Mon compte LinkedIn** | Relier votre compte LinkedIn (nom, photo) pour publier un post depuis le studio, et accéder à l’import de vos statistiques. |
| **Calendrier** | Vos publications par jour, date du jour surlignée, vue mobile en agenda. |
| **Publications** | Liste, tableau de production et galerie ; texte, accroches, photo, notes, statut, mesures, bouton « Publier sur LinkedIn ». |
| **Assistant LinkedIn** | **Récit d’expérience** (méthode du skill `redaction-post-linkedin` : accroche, problème, compétence transférable, propositions, nuance, question), **formules d’accroche** (21 formules de `li-post`), amélioration et conversation avec Claude, vérification anti-« texte IA », profil de voix. Les deux rédacteurs fonctionnent sans IA. |
| **Idées de posts** | Noter une idée en vrac, la retravailler, la transformer en publication. |
| **Contenus consommés** | Podcasts, vidéos, livres, articles ; un lien partagé depuis YouTube, Spotify ou Apple Podcasts crée la fiche tout seul. |
| **GitHub** | Vos dépôts deviennent des idées de posts sur ce que vous avez réalisé. |
| **Impact LinkedIn** | Import de l’export officiel de vos statistiques (XLSX ou CSV), taux d’engagement, évolution. |
| **Benchmark international** | 30 créateurs produit observés (France / États-Unis) comme source d’inspiration, avec vos favoris et notes. |
| **Sujets & stratégie** | Positionnement, piliers et répartition de vos posts. |
| **Sauvegardes** | Export ZIP, JSON et CSV de toutes vos données. |

## Démarrer en local (5 minutes)

Python 3.10 ou plus récent.

```sh
git clone https://github.com/manondesclaux/studio-editorial-linkedin.git
cd studio-editorial-linkedin
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Ouvrez http://localhost:8501, puis suivez l’accueil : **Personnalisation**, **Mon compte LinkedIn**, puis **Assistant LinkedIn**. Sur Mac, un double-clic sur `lancer.command` fait la même chose.

Sans autre réglage, les données sont enregistrées dans `data/personnel/` (base SQLite), sur votre ordinateur uniquement.

## Réglages facultatifs

Copiez `.streamlit/secrets.toml.exemple` en `.streamlit/secrets.toml` (jamais envoyé sur GitHub) et remplissez ce dont vous avez besoin :

| Réglage | Pour quoi faire | Où l’obtenir |
|---|---|---|
| `DATABASE_URL` | Garder vos données en ligne (téléphone + ordinateur) | [Supabase](https://supabase.com), gratuit → Connect → Session pooler |
| `ANTHROPIC_API_KEY` | « Améliorer la rédaction » et la conversation IA | [platform.claude.com](https://platform.claude.com) → API Keys (facturé à l’usage) |
| `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `APP_URL` | Relier votre compte et publier depuis le studio | Votre application sur [LinkedIn Developers](https://www.linkedin.com/developers/apps), voir l’onglet Mon compte LinkedIn |
| `GITHUB_TOKEN` | Inclure vos dépôts privés dans l’onglet GitHub | GitHub → Settings → Developer settings |

Ce qui marche sans aucune clé : calendrier, publications, idées, contenus, rédacteur guidé, vérification des textes, import des statistiques, benchmark, sauvegardes.

## Mettre le studio en ligne et sur son téléphone

Guide pas à pas (Supabase, Streamlit Community Cloud, icône sur l’écran d’accueil, raccourci iPhone « Ajouter au studio ») : [MISE-EN-LIGNE.md](MISE-EN-LIGNE.md).

## Statistiques LinkedIn : ce qui est possible

LinkedIn ne donne pas aux applications l’accès aux statistiques des profils personnels sans partenariat validé. Le studio importe donc l’export officiel : profil → Statistiques → Impressions des posts → **Exporter**. Les chiffres sont rattachés à chaque publication grâce à son lien. La connexion LinkedIn sert à afficher votre compte et à publier.

## Crédits

- Skills LinkedIn (`skills/`) : [Jakeschincariol/linkedin-agent-skill](https://github.com/Jakeschincariol/linkedin-agent-skill), licence MIT (voir `skills/LICENSE`). Les 21 formules d’accroche et les règles de rédaction sont adaptées en français dans `redacteur.py`.
- Application : [Streamlit](https://streamlit.io), assistant IA [Claude](https://www.anthropic.com).

Licence : MIT, voir [LICENSE](LICENSE).
