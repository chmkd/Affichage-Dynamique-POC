# 📦 Checklist de déploiement - Player Affichage Dynamique

## ✅ Contenu du dossier Player

### Fichiers principaux (4)
- [x] `affichageDynamique.py` - Script principal (980 lignes)
- [x] `README.md` - Documentation complète
- [x] `requirements.txt` - Liste des dépendances Python
- [x] `check_installation.py` - Script de vérification

### Dossier icons/ (13 fichiers PNG)
- [x] `sunny.png` - Icône météo ensoleillé
- [x] `cloudy.png` - Icône météo nuageux
- [x] `rainy.png` - Icône météo pluvieux
- [x] `windy.png` - Icône météo venteux
- [x] `junia.png` - Logo JUNIA
- [x] `ilevia.png` - Logo Ilévia
- [x] `temp.png` - Icône température
- [x] `humidity.png` - Icône humidité
- [x] `vlille.png` - Logo V'lille
- [x] `busL5aller.png` - Icône bus L5 aller
- [x] `busL5retour.png` - Icône bus L5 retour
- [x] `bus18aller.png` - Icône bus 18 aller
- [x] `bus18retour.png` - Icône bus 18 retour

### Dossiers créés automatiquement
- [ ] `downloads/` - Contenus serveur (créé au lancement)
- [ ] `cache/` - Cache données API (créé au lancement)

---

## 🚀 Procédure de déploiement

### 1️⃣ Copier le dossier Player
```bash
# Copier l'intégralité du dossier Player vers la destination
cp -r Player/ /destination/path/
```

### 2️⃣ Installer Python 3.7+
```bash
python --version
# Doit afficher Python 3.7 ou supérieur
```

### 3️⃣ Installer les dépendances
```bash
cd Player
pip install -r requirements.txt
```

Ou manuellement :
```bash
pip install pygame opencv-python requests
```

### 4️⃣ Vérifier l'installation
```bash
python check_installation.py
```

**Résultat attendu :**
```
✅ INSTALLATION COMPLÈTE ET FONCTIONNELLE
🚀 Pour lancer l'application :
   python affichageDynamique.py
```

### 5️⃣ Configuration (optionnel)
Éditer `affichageDynamique.py` (lignes 20-48) :
- URL serveur de contenus
- Stations bus et V'lille
- Durées d'affichage
- Lignes de bus

### 6️⃣ Lancer l'application
```bash
python affichageDynamique.py
```

**Mode plein écran automatique**
- ESC ou Q pour quitter
- ESPACE pour synchroniser
- FLÈCHE DROITE pour page suivante

---

## 🔧 Configuration du serveur de contenus

### API requise

Le serveur doit fournir ces endpoints :

**Test connexion :**
```
GET http://192.168.1.20:8090/api/ping
→ {"message": "OK"}
```

**Liste contenus :**
```
GET http://192.168.1.20:8090/api/contents
→ [
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

### Sans serveur

L'application fonctionne **sans serveur** avec uniquement les 3 pages API :
- Bus Ilévia
- Météo
- V'lille

---

## 📊 Vérification des icônes

Toutes les icônes doivent être au format PNG et placées dans `icons/` :

| Fichier | Utilisation | Taille recommandée |
|---------|-------------|-------------------|
| sunny.png | Météo ensoleillé | 150×150 |
| cloudy.png | Météo nuageux | 150×150 |
| rainy.png | Météo pluvieux | 150×150 |
| windy.png | Météo venteux | 150×150 |
| temp.png | Température | 100×100 |
| humidity.png | Humidité | 100×100 |
| junia.png | Logo JUNIA | Variable (ratio préservé) |
| ilevia.png | Logo Ilévia | Variable (ratio préservé) |
| vlille.png | Logo V'lille | Variable (ratio préservé) |
| busL5aller.png | Bus L5 → | 100×40 |
| busL5retour.png | Bus L5 ← | 100×40 |
| bus18aller.png | Bus 18 → | 100×40 |
| bus18retour.png | Bus 18 ← | 100×40 |

---

## 🐛 Résolution de problèmes

### Problème : Icônes manquantes (carrés gris)
**Solution :** Vérifier que `icons/` contient les 13 PNG

### Problème : "Module pygame not found"
**Solution :** `pip install pygame`

### Problème : "Module cv2 not found"
**Solution :** `pip install opencv-python`

### Problème : Connexion serveur échouée
**Solution :** L'application continue avec pages API uniquement

### Problème : Pages API vides
**Solution :** Vérifier connexion Internet et attendre 60s

### Problème : Vidéo ne se lance pas
**Solution :** Vérifier que le fichier est dans `downloads/`

---

## 📝 Changelog

### Version 1.0 - Novembre 2025
- ✅ Combinaison pages API + contenus serveur
- ✅ Optimisation lecture vidéo OpenCV
- ✅ Synchronisation automatique (60s)
- ✅ Panneau temps réel (heure, météo, bus, V'lille)
- ✅ Rotation automatique des pages
- ✅ Support vidéos/images plein écran
- ✅ Gestion priorités et planification

---

## 📞 Support

Pour toute question :
1. Consulter `README.md`
2. Exécuter `python check_installation.py`
3. Vérifier les logs en console

---

**Dossier Player prêt pour déploiement ! 🎉**
