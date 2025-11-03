# 📺 Affichage Dynamique JUNIA - Player

## 📋 Description

Application d'affichage dynamique combinant :
- **Pages API** : Bus Ilévia, Météo, V'lille (avec panneau d'informations temps réel)
- **Contenus serveur** : Vidéos et images synchronisées depuis un serveur distant

## 📁 Structure du dossier

```
Player/
├── affichageDynamique.py    # Script principal
├── icons/                    # Icônes nécessaires (13 fichiers PNG)
│   ├── sunny.png
│   ├── cloudy.png
│   ├── rainy.png
│   ├── windy.png
│   ├── junia.png
│   ├── ilevia.png
│   ├── temp.png
│   ├── humidity.png
│   ├── vlille.png
│   ├── busL5aller.png
│   ├── busL5retour.png
│   ├── bus18aller.png
│   └── bus18retour.png
├── downloads/                # (créé automatiquement) Contenus serveur téléchargés
├── cache/                    # (créé automatiquement) Cache des données API
└── README.md                 # Ce fichier
```

## 🔧 Prérequis

### Python 3.7+

**Bibliothèques Python requises :**
```bash
pip install pygame opencv-python requests
```

Ou avec le fichier requirements.txt :
```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

### Éditer `affichageDynamique.py` (lignes 20-40)

**URLs API (déjà configurées pour Lille Métropole) :**
- `API_URL` : Bus Ilévia
- `VLILLE_URL` : Stations V'lille
- `METEO_URL` : Météo Open-Meteo
- `ACTUAL_URL` : Météo actuelle

**Serveur de contenus :**
```python
SERVER_URL = "http://192.168.1.20:8090"  # Modifier selon votre serveur
CONTENT_SYNC_INTERVAL = 60               # Synchronisation toutes les 60s
```

**Stations à afficher :**
```python
NOM_STATION = "SOLFERINO"                # Arrêt de bus
STATION_VLILLE = "PALAIS RAMEAU"         # Station V'lille
```

**Durées d'affichage :**
```python
API_PAGE_DURATION = 10       # Durée pages Bus/Météo/V'lille (secondes)
MEDIA_DURATION_DEFAULT = 20  # Durée par défaut vidéos/images (secondes)
```

**Lignes de bus :**
```python
DIRECTIONS = {
    "L5": ["MARCQ FERME AUX OIES", "HAUBOURDIN LE PARC"],
    "18": ["LOMME ANATOLE FRANCE", "VILLENEUVE D'ASCQ HOTEL DE VILLE"]
}
```

## 🚀 Lancement

### Mode normal (plein écran)
```bash
python affichageDynamique.py
```

### Raccourcis clavier pendant l'exécution
- **ESC** ou **Q** : Quitter l'application
- **ESPACE** : Forcer synchronisation manuelle (API + serveur)
- **FLÈCHE DROITE** : Passer à la page suivante

## 🔄 Rotation des pages

L'application affiche en boucle :

1. **Page Bus** (10s) - Prochains passages + frise temporelle + panneau droit
2. **Page Météo** (10s) - Météo actuelle + prévisions 3 jours + panneau droit
3. **Page V'lille** (10s) - Disponibilité vélos/places + panneau droit
4. **Contenus serveur** (durée configurée) - Vidéos/images en plein écran

### Panneau droit (visible uniquement pour pages API)
- Heure actuelle (grande)
- Météo actuelle (température + humidité)
- V'lille (barre vélos/places)
- Prochains bus (L5 et 18)
- Logos JUNIA + Ilévia

## 🌐 Serveur de contenus

### API requise

Le serveur doit fournir :

**GET /api/ping** - Test connexion
```json
{"message": "OK"}
```

**GET /api/contents** - Liste des contenus
```json
[
  {
    "name": "video1.mp4",
    "url": "http://192.168.1.20:8090/downloads/video1.mp4",
    "type": "video",
    "duration": 30,
    "priority": 3,
    "start_date": "2025-01-01T00:00:00",
    "end_date": "2025-12-31T23:59:59"
  }
]
```

### Synchronisation automatique

- Vérification toutes les 60 secondes
- Téléchargement automatique des nouveaux contenus
- Respect des dates de planification (start_date / end_date)
- Tri par priorité (1=faible, 3=élevée)

## 🎬 Optimisations vidéo

Le lecteur vidéo est optimisé pour :
- **Décodage OpenCV** avec backend FFMPEG
- **Redimensionnement cv2.resize** avec interpolation INTER_NEAREST (10x plus rapide)
- **Timing précis** basé sur time.time() et FPS réel de la vidéo
- **Lecture en boucle** si la durée configurée dépasse la durée de la vidéo

## 📊 Sources de données

- **Bus Ilévia** : data.lillemetropole.fr (API temps réel)
- **V'lille** : data.lillemetropole.fr (WFS temps réel)
- **Météo** : api.open-meteo.com (prévisions 3 jours)
- **Contenus** : Serveur local configurable

## 🐛 Dépannage

### Erreur "Impossible d'ouvrir la vidéo"
- Vérifier que le fichier existe dans `downloads/`
- Vérifier que OpenCV est installé : `pip install opencv-python`

### Erreur "Connexion serveur échouée"
- Vérifier que le serveur est accessible : `http://192.168.1.20:8090/api/ping`
- L'application continue de fonctionner avec les pages API uniquement

### Icônes manquantes (carrés gris)
- Vérifier que le dossier `icons/` contient les 13 fichiers PNG
- Chemins relatifs : lancer depuis le dossier `Player/`

### Pages API vides
- Vérifier la connexion Internet
- Attendre 60 secondes (synchronisation automatique)
- Appuyer sur ESPACE pour forcer la synchronisation

## 📦 Portabilité

Pour déployer sur un autre PC :

1. Copier l'intégralité du dossier `Player/`
2. Installer Python 3.7+ et les dépendances
3. Modifier la configuration si nécessaire
4. Lancer `python affichageDynamique.py`

**Aucune dépendance externe** autre que les bibliothèques Python listées.

## 📝 Licence

Projet JUNIA - Affichage Dynamique POC
