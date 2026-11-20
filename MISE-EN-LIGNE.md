# Utiliser le studio sur le téléphone

Objectif : le studio en ligne, accessible partout (même Mac éteint), réservé à vous, avec un bouton sur l’écran d’accueil de l’iPhone et un raccourci « Ajouter au studio » dans le menu Partager de Podcasts, Spotify et YouTube.

Trois services gratuits :

- **Supabase** garde vos données (base Postgres en ligne).
- **Streamlit Community Cloud** fait tourner l’application depuis votre dépôt GitHub privé.
- **Raccourcis** (app Apple déjà sur l’iPhone) envoie les liens partagés au studio.

Comptez 20 minutes la première fois.

## 1. Créer la base de données (Supabase)

1. Allez sur [supabase.com](https://supabase.com) → **Start your project**, connectez-vous avec GitHub.
2. **New project** : nom `studio-editorial`, mot de passe de base (notez-le), région **West EU (Paris)**, offre **Free**.
3. Une fois le projet prêt : bouton **Connect** en haut → onglet **Connection string** → section **Session pooler**. Copiez l’adresse (elle commence par `postgresql://postgres.`) et remplacez `[YOUR-PASSWORD]` par votre mot de passe.

À savoir : sur l’offre gratuite, un projet inutilisé pendant 7 jours est mis en pause. Un clic sur **Restore** dans Supabase le relance, sans perte de données.

## 2. Copier vos données actuelles en ligne

Sur le Mac, dans le dossier du projet :

1. Copiez `.streamlit/secrets.toml.exemple` en `.streamlit/secrets.toml`.
2. Collez votre adresse Supabase à la place de l’exemple sur la ligne `DATABASE_URL`. Ajoutez votre clé API Anthropic si vous en avez une.
3. Dans le terminal de VS Code :

```sh
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python migrer_en_ligne.py
```

Le script affiche le nombre de publications, idées, contenus, statistiques et photos copiés. Vos données locales restent intactes.

Avec ce fichier `secrets.toml`, le studio lancé sur le Mac utilise lui aussi la base en ligne : le Mac et le téléphone voient les mêmes données. La barre latérale indique « Base en ligne ». Ce fichier n’est jamais envoyé sur GitHub.

## 3. Mettre l’application en ligne (Streamlit Community Cloud)

1. Allez sur [share.streamlit.io](https://share.streamlit.io) → **Continue with GitHub**, autorisez l’accès à vos dépôts privés.
2. **Create app** → **Deploy a public app from GitHub** :
   - Repository : votre copie du dépôt (bouton **Fork** sur GitHub), par exemple `votre-compte/studio-editorial-linkedin`
   - Branch : `main`
   - Main file path : `app.py`
   - App URL : choisissez un nom, par exemple `studio-prenom-nom`
3. **Advanced settings** : Python **3.12**, puis dans **Secrets** collez le contenu de votre `.streamlit/secrets.toml`.
4. **Deploy**. Le premier démarrage prend quelques minutes.
5. Rendez l’application privée : **Settings → Sharing** → *Who can view this app* → **Only specific people can view this app**, puis ajoutez votre adresse e-mail. Le code est public, vos données ne le sont pas : elles restent dans votre base Supabase, mais l’application, elle, doit être réservée à vous.

À savoir : après plusieurs jours sans visite, l’application se met en veille. La première ouverture affiche alors un bouton pour la réveiller (environ 30 secondes).

## 4. Relier votre compte LinkedIn (facultatif)

Pour publier depuis le studio, créez votre application LinkedIn en suivant l’onglet **Mon compte LinkedIn** (environ 10 minutes, une page LinkedIn est nécessaire). Dans *Authorized redirect URLs*, déclarez l’adresse de votre studio en ligne, avec la barre finale, par exemple `https://studio-prenom-nom.streamlit.app/`. Ajoutez ensuite dans les secrets de l’application :

```toml
LINKEDIN_CLIENT_ID = "…"
LINKEDIN_CLIENT_SECRET = "…"
APP_URL = "https://studio-prenom-nom.streamlit.app"
```

## Protéger le studio (à faire avant de le partager)

Le studio peut publier sur votre LinkedIn : ne le laissez pas ouvert à tous. Ajoutez dans les secrets de l’application (Settings → Secrets) :

```toml
APP_PASSWORD = "une phrase longue et unique"
```

Le studio demande alors ce mot de passe à l’ouverture (5 essais ratés = blocage de 5 minutes). Gardez aussi le réglage **Only specific people can view this app**. Le studio active lui-même la protection RLS sur vos tables Supabase, et les sauvegardes ZIP ne contiennent jamais votre jeton LinkedIn.

## 5. Le studio sur l’écran d’accueil de l’iPhone

1. Ouvrez l’adresse de votre application dans **Safari** et connectez-vous.
2. Bouton **Partager** → **Sur l’écran d’accueil** → **Ajouter**.

Une icône « Studio éditorial » s’ouvre ensuite en plein écran, comme une application. Sur téléphone, le menu des onglets s’ouvre avec la flèche en haut à gauche.

## 6. Le raccourci « Ajouter au studio »

Il ajoute n’importe quel épisode, vidéo ou article à l’onglet **Contenus consommés** depuis le bouton Partager. Le studio retrouve seul le titre, l’émission ou la chaîne et le type de contenu.

Dans l’app **Raccourcis** de l’iPhone :

1. **+** pour créer un raccourci, nommez-le **Ajouter au studio**.
2. Touchez **ⓘ** (ou le nom en haut) → activez **Afficher dans la feuille de partage**. Dans les types acceptés, gardez **URL** et **Texte** (Spotify et YouTube partagent parfois du texte qui contient le lien).
3. Ajoutez ces actions, dans l’ordre :
   1. **Obtenir les URL de l’entrée** (Get URLs from Input), appliquée à **Entrée du raccourci**.
   2. **Obtenir l’élément de la liste** (Get Item from List) → **Premier élément**.
   3. **Encoder l’URL** (URL Encode) sur cet élément.
   4. **Texte** : `https://VOTRE-APP.streamlit.app/?ajout=`, puis insérez la variable **Texte encodé** juste après le `=`.
   5. **Ouvrir les URL** sur ce texte.
4. Remplacez `VOTRE-APP` par le nom choisi à l’étape 3.

Pour l’utiliser : dans Podcasts, Spotify ou YouTube, **Partager** → **Ajouter au studio**. Le studio s’ouvre sur la fiche ajoutée, où vous pouvez noter tout de suite ce que vous en retenez, ou plus tard.

Sans le raccourci, l’onglet **Contenus consommés → Ajouter depuis un lien** fait la même chose par copier-coller.

## Mettre à jour l’application en ligne

Chaque envoi sur la branche `main` du dépôt GitHub met à jour l’application en ligne automatiquement en une à deux minutes.
