# StudioSowa — Site Web

Site d'architecture bilingue (FR/EN) avec interface d'administration.

## Installation rapide

### 1. Prérequis
- Python 3.9 ou plus récent
- pip

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Lancer le site

```bash
python run.py
```

Le site est ensuite accessible à :
- **Site public** → http://localhost:5000
- **Administration** → http://localhost:5000/admin

### 4. Mot de passe admin

Par défaut : **sowa2024!**

Pour le changer, créez un fichier `.env` à la racine du projet :
```
ADMIN_PASSWORD=votre-mot-de-passe-ici
```

---

## Structure du projet

```
StudioSowa/
├── app.py              ← Application principale (backend Flask)
├── run.py              ← Lanceur (python run.py)
├── requirements.txt    ← Dépendances Python
├── studiosowa.db       ← Base de données (créée automatiquement)
├── static/
│   ├── css/main.css    ← Styles du site
│   ├── js/main.js      ← JavaScript frontend
│   ├── js/admin.js     ← JavaScript administration
│   └── uploads/        ← Images uploadées (créé automatiquement)
└── templates/
    ├── base.html        ← Gabarit de base
    ├── index.html       ← Page d'accueil (grille de projets)
    ├── project.html     ← Page détail projet
    ├── studio.html      ← Page "Studio"
    ├── contact.html     ← Page contact
    └── admin/
        ├── login.html       ← Connexion admin
        ├── dashboard.html   ← Liste des projets
        └── project_form.html ← Formulaire projet
```

---

## Gestion des projets (Administration)

1. Aller sur http://localhost:5000/admin
2. Se connecter avec le mot de passe
3. Cliquer **"Nouveau projet"** pour créer un projet
4. Remplir le formulaire :
   - Titre en français et en anglais
   - Localisation, année, architecte, client, phase, surface
   - Description dans les deux langues
   - Taille dans la grille (Grand = 8 colonnes / Moyen = 4 colonnes)
   - Ordre d'affichage (0 = en premier)
5. Cliquer **"Créer le projet"**
6. Après création, ajouter les images dans l'onglet "Images" du projet

### Gestion des images
- Drag & drop ou clic pour uploader
- Glisser-déposer pour réorganiser
- ★ pour définir la vignette principale (image affichée dans la grille)
- × pour supprimer une image

---

## Déploiement en production

Pour mettre le site en ligne (ex: sur un VPS Ubuntu) :

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Ou utiliser un service comme **Railway**, **Render**, ou **PythonAnywhere**.

---

## Personnalisation

### Contenu du Studio
Modifier le fichier `templates/studio.html` pour mettre à jour :
- Le texte de présentation (FR/EN)
- Les statistiques (années d'expérience, projets, pays)

### Contact
Modifier `templates/contact.html` pour mettre à jour l'adresse, email, téléphone.

### Couleurs / Police
Tout est dans `static/css/main.css` — section "CSS Custom Properties" en haut du fichier.
