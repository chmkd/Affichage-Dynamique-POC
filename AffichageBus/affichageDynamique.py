#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Affichage Dynamique JUNIA - Version Combinée
Combine les pages API (Bus, Météo, V'lille) avec les contenus serveur (vidéos/images)
"""

import os
import sys
import time
import json
import requests
import pygame
import cv2
from threading import Thread
from datetime import datetime, timedelta

# ==================== CONFIGURATION ====================

# URLs API
API_URL = "https://data.lillemetropole.fr/data/ogcapi/collections/ilevia:prochains_passages/items?f=json&limit=-1"
VLILLE_URL = "https://data.lillemetropole.fr/geoserver/wfs?SERVICE=WFS&REQUEST=GetFeature&VERSION=2.0.0&TYPENAMES=dsp_ilevia%3Avlille_temps_reel&OUTPUTFORMAT=application%2Fjson"
METEO_URL = "https://api.open-meteo.com/v1/forecast?latitude=50.6333&longitude=3.0667&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,weather_code&current_weather=true&timezone=Europe/Paris"
ACTUAL_URL = "https://api.open-meteo.com/v1/forecast?latitude=50.633&longitude=3.0586&models=meteofrance_seamless&current=temperature_2m,relative_humidity_2m&forecast_days=1"

# Serveur de contenus
SERVER_URL = "http://192.168.1.20:8090"
CONTENT_SYNC_INTERVAL = 60  # Synchronisation toutes les 60 secondes

# Stations
NOM_STATION = "SOLFERINO"
STATION_VLILLE = "PALAIS RAMEAU"

# Durées d'affichage (en secondes)
API_PAGE_DURATION = 10  # Bus, Météo, V'lille
MEDIA_DURATION_DEFAULT = 20  # Contenus serveur par défaut

# Dossiers
DOWNLOADS_FOLDER = "downloads"
CACHE_FOLDER = "cache"
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
os.makedirs(CACHE_FOLDER, exist_ok=True)

# Directions bus
DIRECTIONS = {
    "L5": ["MARCQ FERME AUX OIES", "HAUBOURDIN LE PARC"],
    "18": ["LOMME ANATOLE FRANCE", "VILLENEUVE D'ASCQ HOTEL DE VILLE"]
}

# ==================== INITIALISATION PYGAME ====================

pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.mouse.set_visible(False)
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h

# Layout : 2/3 gauche pour contenu principal, 1/3 droite pour panneau info
LEFT_W = WIDTH * 2 // 3
RIGHT_W = WIDTH - LEFT_W
LEFT_RECT = pygame.Rect(0, 0, LEFT_W, HEIGHT)
RIGHT_RECT = pygame.Rect(LEFT_W, 0, RIGHT_W, HEIGHT)

# Polices
font = pygame.font.Font(None, 60)
small_font = pygame.font.Font(None, 50)
meteopanel_font = pygame.font.Font(None, 70)

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 102, 204)
GREEN = (0, 153, 0)
RED = (255, 0, 0)
GRAY = (200, 200, 200)
DARK_RED = (139, 0, 0)
LIGHT_BLUE = (173, 216, 230)
DARK_BLUE = (70, 130, 180)
ORANGE = (252, 93, 51)
PURPLE = (63, 42, 85)

# Clock pour contrôle FPS
clock = pygame.time.Clock()

# ==================== CHARGEMENT ICÔNES ====================

def load_and_scale(path, size):
    """Charge et redimensionne une image"""
    try:
        img = pygame.image.load(path)
        return pygame.transform.smoothscale(img, size)
    except Exception as e:
        print(f"⚠️  Erreur chargement {path}: {e}")
        # Retourner une surface vide en cas d'erreur
        surf = pygame.Surface(size)
        surf.fill(GRAY)
        return surf

# Icônes météo
weather_icons = {
    "sunny": load_and_scale("icons/sunny.png", (150, 150)),
    "cloudy": load_and_scale("icons/cloudy.png", (150, 150)),
    "rainy": load_and_scale("icons/rainy.png", (150, 150)),
    "windy": load_and_scale("icons/windy.png", (150, 150))
}

# Logos
LOGO_H = 60
logo_junia = load_and_scale("icons/junia.png", (int(200 * LOGO_H / 60), LOGO_H))
logo_ilevia = load_and_scale("icons/ilevia.png", (int(200 * LOGO_H / 60), LOGO_H))
logos = [logo_junia, logo_ilevia]

# Icônes bus
ICON_SIZE = 40
bus_icons = {}
for line in ["L5", "18"]:
    bus_icons[line] = {
        "aller": load_and_scale(f"icons/bus{line}aller.png", (int(ICON_SIZE * 2.5), ICON_SIZE)),
        "retour": load_and_scale(f"icons/bus{line}retour.png", (int(ICON_SIZE * 2.5), ICON_SIZE))
    }

# ==================== CACHE DONNÉES API ====================

cache = {
    "actual": {},
    "forecast": None,
    "vlille": None,
    "bus_next": {},
    "bus_records": [],
    "last_update": None,
    "last_error": None
}

# ==================== GESTIONNAIRE DE CONTENUS SERVEUR ====================

class ContentManager:
    """Gestionnaire de contenus avec synchronisation serveur"""
    
    def __init__(self):
        self.server_contents = []
        self.last_sync = 0
        self.sync_thread = None
        self.running = True
        
    def test_server_connection(self):
        """Test de connexion au serveur"""
        try:
            response = requests.get(f"{SERVER_URL}/api/ping", timeout=5)
            if response.status_code == 200:
                print(f"✅ Serveur connecté: {response.json().get('message', 'OK')}")
                return True
            else:
                print(f"❌ Serveur erreur HTTP: {response.status_code}")
                return False
        except requests.RequestException as e:
            print(f"❌ Connexion serveur échouée: {e}")
            return False
    
    def sync_contents(self):
        """Synchronisation des contenus depuis le serveur"""
        try:
            print("🔄 Synchronisation des contenus...")
            
            response = requests.get(f"{SERVER_URL}/api/contents", timeout=10)
            if response.status_code != 200:
                print(f"❌ Erreur API: {response.status_code}")
                return False
            
            contents = response.json()
            print(f"📋 {len(contents)} contenus trouvés sur le serveur")
            
            # Télécharger les nouveaux contenus
            downloaded = 0
            for content in contents:
                filename = content['name']
                filepath = os.path.join(DOWNLOADS_FOLDER, filename)
                
                if not os.path.exists(filepath):
                    try:
                        print(f"⬇️  Téléchargement: {filename}")
                        file_response = requests.get(content['url'], timeout=30)
                        
                        if file_response.status_code == 200:
                            with open(filepath, 'wb') as f:
                                f.write(file_response.content)
                            downloaded += 1
                            print(f"✅ Téléchargé: {filename}")
                        else:
                            print(f"❌ Erreur téléchargement {filename}: {file_response.status_code}")
                    except Exception as e:
                        print(f"❌ Erreur téléchargement {filename}: {e}")
            
            self.server_contents = contents
            self.last_sync = time.time()
            
            if downloaded > 0:
                print(f"✅ {downloaded} nouveaux fichiers téléchargés")
            else:
                print("✅ Tous les fichiers sont à jour")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur synchronisation: {e}")
            return False
    
    def get_available_contents(self):
        """Récupère les contenus disponibles localement"""
        available = []
        
        for content in self.server_contents:
            filepath = os.path.join(DOWNLOADS_FOLDER, content['name'])
            if os.path.exists(filepath):
                now = datetime.now()
                
                # Vérifier dates de planification
                if content.get('start_date'):
                    start_date = datetime.fromisoformat(content['start_date'])
                    if now < start_date:
                        continue
                
                if content.get('end_date'):
                    end_date = datetime.fromisoformat(content['end_date'])
                    if now > end_date:
                        continue
                
                available.append({
                    'filepath': filepath,
                    'duration': content.get('duration', MEDIA_DURATION_DEFAULT),
                    'type': content.get('type', 'image'),
                    'priority': content.get('priority', 2),
                    'name': content['name']
                })
        
        # Trier par priorité (plus haute en premier)
        available.sort(key=lambda x: x['priority'], reverse=True)
        return available
    
    def start_sync_thread(self):
        """Démarre le thread de synchronisation automatique"""
        def sync_loop():
            while self.running:
                self.sync_contents()
                time.sleep(CONTENT_SYNC_INTERVAL)
        
        self.sync_thread = Thread(target=sync_loop, daemon=True)
        self.sync_thread.start()
        print(f"🔄 Synchronisation automatique démarrée (toutes les {CONTENT_SYNC_INTERVAL}s)")
    
    def stop(self):
        """Arrête le gestionnaire de contenus"""
        self.running = False

# ==================== FONCTIONS RÉCUPÉRATION API ====================

def fetch_actual():
    """Récupère la météo actuelle"""
    try:
        r = requests.get(ACTUAL_URL, timeout=5)
        r.raise_for_status()
        d = r.json()
        current = d.get("current", {})
        cache["actual"]["temperature"] = current.get("temperature_2m", cache["actual"].get("temperature"))
        cache["actual"]["humidity"] = current.get("relative_humidity_2m", cache["actual"].get("humidity"))
        cache["last_error"] = None
    except Exception as e:
        cache["last_error"] = f"Actuelle : {e}"
    return cache["actual"]

def fetch_forecast():
    """Récupère les prévisions météo"""
    try:
        r = requests.get(METEO_URL, timeout=10)
        r.raise_for_status()
        cache["forecast"] = r.json()["daily"]
        cache["last_error"] = None
    except Exception as e:
        cache["last_error"] = f"Météo: {e}"
    return cache["forecast"]

def fetch_vlille():
    """Récupère les données V'lille"""
    try:
        r = requests.get(VLILLE_URL, timeout=10)
        r.raise_for_status()
        for f in r.json().get("features", []):
            p = f["properties"]
            if p.get("nom") == STATION_VLILLE:
                cache["vlille"] = {
                    "nb_velos": p.get("nb_velos_dispo", 0),
                    "nb_places": p.get("nb_places_dispo", 0)
                }
                break
        cache["last_error"] = None
    except Exception as e:
        cache["last_error"] = f"V'Lille: {e}"
    return cache["vlille"]

def fetch_bus_next():
    """Récupère les prochains bus"""
    try:
        r = requests.get(API_URL, timeout=10)
        r.raise_for_status()
        recs = r.json().get("records", [])
        if recs:
            cache["bus_records"] = recs
        
        nxt = {}
        for line in ["L5", "18"]:
            times = []
            for it in cache["bus_records"]:
                if it.get("code_ligne") == line and it.get("nom_station") == NOM_STATION:
                    try:
                        dt = datetime.fromisoformat(it["heure_estimee_depart"])
                        if dt.tzinfo:
                            dt = dt.replace(tzinfo=None)
                        times.append(dt)
                    except:
                        pass
            if times:
                nxt[line] = min(times)
        cache["bus_next"] = nxt
        cache["last_error"] = None
    except Exception as e:
        cache["last_error"] = f"Bus: {e}"
    return cache["bus_next"]

def update_all_api_data():
    """Met à jour toutes les données API"""
    fetch_actual()
    fetch_vlille()
    fetch_bus_next()
    fetch_forecast()
    cache["last_update"] = datetime.now()

# ==================== PANNEAU DROIT (INFO TEMPS RÉEL) ====================

def draw_right_panel():
    """Affiche le panneau de droite avec infos en temps réel"""
    pygame.draw.rect(screen, PURPLE, RIGHT_RECT)
    x0 = LEFT_W + 20

    # Heure
    time_font = pygame.font.Font(None, 250)
    time_str = datetime.now().strftime("%H:%M")
    time_surf = time_font.render(time_str, True, ORANGE)
    time_x = LEFT_W + (RIGHT_W - time_surf.get_width()) // 2
    screen.blit(time_surf, (time_x, 50))

    # Météo actuelle
    title_font = pygame.font.Font(None, 60)
    value_font = pygame.font.Font(None, 50)

    actual = cache["actual"]
    block_x, block_y = x0, 250
    block_w, block_h = RIGHT_W - 40, 200
    pygame.draw.rect(screen, WHITE, (block_x, block_y, block_w, block_h), border_radius=12)

    title_txt = title_font.render("Météo actuelle", True, BLACK)
    title_x = block_x + (block_w - title_txt.get_width()) // 2
    screen.blit(title_txt, (title_x, block_y + 25))

    content_top = block_y + 10 + title_txt.get_height() + 30

    ICON_SIZE = 100
    icon_temp = load_and_scale("icons/temp.png", (ICON_SIZE, ICON_SIZE))
    icon_humid = load_and_scale("icons/humidity.png", (ICON_SIZE, ICON_SIZE))
    
    t = actual.get("temperature", "--")
    h = actual.get("humidity", "--")
    txt_temp = meteopanel_font.render(f"{t}°C", True, BLACK)
    txt_humid = meteopanel_font.render(f"{h}%", True, BLACK)

    sep_x = block_x + block_w // 2 + 20
    sep_y0 = block_y + 25 + title_txt.get_height() + 10
    sep_y1 = block_y + block_h - 25
    pygame.draw.line(screen, GRAY, (sep_x, sep_y0), (sep_x, sep_y1), 2)

    left_mid = block_x + block_w // 4
    right_mid = block_x + 3 * block_w // 4

    group_w1 = ICON_SIZE + 10 + txt_temp.get_width()
    start_x1 = left_mid - group_w1 // 2
    y_icon = content_top
    y_text = y_icon + (ICON_SIZE - txt_temp.get_height()) // 2
    screen.blit(icon_temp, (start_x1, y_icon))
    screen.blit(txt_temp, (start_x1 + ICON_SIZE + 10, y_text))

    group_w2 = ICON_SIZE + 10 + txt_humid.get_width()
    start_x2 = right_mid - group_w2 // 2
    screen.blit(icon_humid, (start_x2, y_icon))
    screen.blit(txt_humid, (start_x2 + ICON_SIZE + 10, y_text))

    # V'lille
    vlille_block = pygame.Rect(x0, block_y + block_h + 20, block_w, 180)
    pygame.draw.rect(screen, WHITE, vlille_block, border_radius=12)

    title2 = font.render(f"V'Lille – {STATION_VLILLE}", True, BLACK)
    title2_x = vlille_block.x + (vlille_block.w - title2.get_width()) // 2
    screen.blit(title2, (title2_x, vlille_block.y + 25))

    vl = cache["vlille"] or {"nb_velos": 0, "nb_places": 0}
    nbv, nbp = vl["nb_velos"], vl["nb_places"]
    total = nbv + nbp or 1
    pct_v = nbv / total
    bar_x = vlille_block.x + 10
    bar_y = vlille_block.y + 95
    bar_w = vlille_block.w - 20
    bar_h = 24
    red_w = int(bar_w * pct_v)
    green_w = bar_w - red_w
    pygame.draw.rect(screen, DARK_BLUE, (bar_x, bar_y, red_w, bar_h), border_radius=8)
    pygame.draw.rect(screen, GREEN, (bar_x + red_w, bar_y, green_w, bar_h), border_radius=8)

    nbv_txt = small_font.render(f"{nbv} vélos", True, BLACK)
    nbp_txt = small_font.render(f"{nbp} places", True, BLACK)
    screen.blit(nbv_txt, (bar_x + 5, bar_y + bar_h + 8))
    screen.blit(nbp_txt, (bar_x + bar_w - nbp_txt.get_width() - 5, bar_y + bar_h + 8))

    # Bus
    bus_block = pygame.Rect(x0, vlille_block.y + vlille_block.h + 20, block_w, 200)
    pygame.draw.rect(screen, WHITE, bus_block, border_radius=12)

    title3 = font.render("Prochains bus – Solférino", True, BLACK)
    title3_x = bus_block.x + (bus_block.w - title3.get_width()) // 2
    screen.blit(title3, (title3_x, bus_block.y + 25))

    now_dt = datetime.now()
    now_min = now_dt.replace(second=0, microsecond=0)
    yy = bus_block.y + 85

    nxt = cache["bus_next"]
    for line, col in [("L5", BLUE), ("18", GREEN)]:
        dt = nxt.get(line)
        if dt:
            delta_min = (dt.hour * 60 + dt.minute) - (now_min.hour * 60 + now_min.minute)
            if delta_min == 0:
                tm, delay = dt.strftime("%H:%M"), "imminent"
            elif delta_min > 0:
                tm, delay = dt.strftime("%H:%M"), f"dans {delta_min} min"
            else:
                tm, delay = "--:--", ""
        else:
            tm, delay = "--:--", ""

        txt_surf = font.render(f"{line} -> {tm}   {delay}", True, col)
        text_x = bus_block.x + (bus_block.w - txt_surf.get_width()) // 2
        screen.blit(txt_surf, (text_x, yy))
        yy += 50

    # Logos
    LOGO_H = 80
    scaled_logos = []
    for img in logos:
        w, h = img.get_size()
        scale_w = int(w * LOGO_H / h)
        scaled = pygame.transform.smoothscale(img, (scale_w, LOGO_H))
        scaled_logos.append(scaled)

    total_w = sum(img.get_width() for img in scaled_logos)
    gap = (RIGHT_W - total_w) // (len(scaled_logos) + 1)
    y_logo = HEIGHT - LOGO_H - 55
    x = LEFT_W + gap
    for img in scaled_logos:
        screen.blit(img, (x, y_logo))
        x += img.get_width() + gap

# ==================== PAGES API ====================

def page_bus():
    """Page Bus (partie gauche + panneau droit)"""
    recs = cache.get("bus_records", [])
    surf = pygame.Surface((LEFT_W, HEIGHT))
    surf.fill(WHITE)

    direction_font = pygame.font.Font(None, 35)

    title_txt = font.render("Bus Ilévia - Arrêt Solférino", True, BLACK)
    title_x = (surf.get_width() - title_txt.get_width()) // 2
    surf.blit(title_txt, (title_x, 20))
    
    y = 80
    now = datetime.now()

    for line, color in [("L5", BLUE), ("18", GREEN)]:
        surf.blit(font.render(line, True, color), (20, y))
        y += 70

        for sens in DIRECTIONS[line]:
            surf.blit(small_font.render(f"{sens} :", True, color), (40, y))
            y += 50

            passages = []
            for it in recs:
                if (it.get("code_ligne") == line
                        and it.get("sens_ligne") == sens
                        and it.get("nom_station") == NOM_STATION):
                    try:
                        dt = datetime.fromisoformat(it["heure_estimee_depart"])
                        if dt.tzinfo:
                            dt = dt.replace(tzinfo=None)
                        passages.append(dt)
                    except:
                        pass
            passages = sorted(passages)[:2]

            now_min = now.replace(second=0, microsecond=0)
            now_total_min = now_min.hour * 60 + now_min.minute

            for dt in passages:
                tm = dt.strftime("%H:%M")
                bus_total_min = dt.hour * 60 + dt.minute
                delta_min = bus_total_min - now_total_min

                if delta_min < 0:
                    continue
                elif delta_min == 0:
                    delay_str = "imminent"
                else:
                    delay_str = f"dans {delta_min} min"

                surf.blit(small_font.render(f"{tm}   {delay_str}", True, BLACK), (60, y))
                y += 50

            y += 10
        y += 45

        # Frise temporelle
        margin = 100
        frise_w = LEFT_W - 2 * margin
        y0 = y

        surf.blit(direction_font.render(DIRECTIONS[line][0], True, BLACK), (margin, y0 - 40))
        end_lbl = direction_font.render(DIRECTIONS[line][1], True, BLACK)
        surf.blit(end_lbl, (margin + frise_w - end_lbl.get_width(), y0 - 40))

        pygame.draw.line(surf, BLACK, (margin, y0), (margin + frise_w, y0), 4)

        for delta, text in [(-20, "20m"), (-10, "10m"), (-5, "5m"), (0, "JUNIA"), (5, "5m"), (10, "10m"), (20, "20m")]:
            x = margin + (delta + 20) * frise_w // 40
            if text == "JUNIA":
                line_color = ORANGE
                line_width = 6
            else:
                line_color = GRAY
                line_width = 2

            pygame.draw.line(surf, line_color, (x, y0 - 10), (x, y0 + 10), line_width)
            text_color = PURPLE if text == "JUNIA" else BLACK
            lbl_surf = small_font.render(text, True, text_color)
            surf.blit(lbl_surf, (x - lbl_surf.get_width() // 2, y0 + 15))

        # Positions bus
        dir_next = {}
        for sens in DIRECTIONS[line]:
            times = []
            for it in recs:
                if (it.get("code_ligne") == line
                        and it.get("sens_ligne") == sens
                        and it.get("nom_station") == NOM_STATION):
                    try:
                        dt = datetime.fromisoformat(it["heure_estimee_depart"])
                        if dt.tzinfo:
                            dt = dt.replace(tzinfo=None)
                        times.append(dt)
                    except:
                        pass
            if times:
                dir_next[sens] = min(times)

        for sens, dt in dir_next.items():
            arr = dt if dt > now else dt + timedelta(days=1)
            dm = round((arr - now).total_seconds() / 60)
            dm += 1
            if -20 <= dm <= 20:
                if sens == DIRECTIONS[line][1]:
                    x = margin + (20 - dm) * frise_w // 40
                    icon = bus_icons[line]["aller"]
                else:
                    x = margin + (dm + 20) * frise_w // 40
                    icon = bus_icons[line]["retour"]
                y_icon = y0 - ICON_SIZE // 2
                surf.blit(icon, (x - ICON_SIZE // 2, y_icon))
        y += 70

    screen.blit(surf, (0, 0))
    draw_right_panel()

def page_weather():
    """Page Météo (partie gauche + panneau droit)"""
    f = cache["forecast"]
    surface = pygame.Surface((LEFT_W, HEIGHT))
    surface.fill(LIGHT_BLUE)

    title_font = pygame.font.Font(None, 90)
    value_font = pygame.font.Font(None, 150)
    date_font = pygame.font.Font(None, 70)
    detail_font = pygame.font.Font(None, 60)

    block_x, block_y = 20, 20
    block_w = LEFT_W - 40
    block_h = 370
    pygame.draw.rect(surface, WHITE, (block_x, block_y, block_w, block_h), border_radius=16)

    title_txt = title_font.render("Météo actuelle", True, BLACK)
    title_x = block_x + (block_w - title_txt.get_width()) // 2
    title_y = block_y + 30
    surface.blit(title_txt, (title_x, title_y))

    if f is None:
        err = font.render("Données météo indisponibles", True, RED)
        surface.blit(err, ((LEFT_W - err.get_width()) // 2, HEIGHT // 2))
        screen.blit(surface, (0, 0))
        draw_right_panel()
        return

    content_top = title_y + title_txt.get_height() + 50

    ICON_SIZE = 200
    icon_temp = load_and_scale("icons/temp.png", (ICON_SIZE, ICON_SIZE))
    icon_humid = load_and_scale("icons/humidity.png", (ICON_SIZE, ICON_SIZE))

    actual = cache["actual"]
    t = actual.get("temperature", "--")
    h = actual.get("humidity", "--")
    txt_temp = value_font.render(f"{t}°C", True, BLACK)
    txt_humid = value_font.render(f"{h}%", True, BLACK)

    sep_x = block_x + block_w // 2
    sep_y0 = title_y + title_txt.get_height() + 20
    sep_y1 = block_y + block_h - 20
    pygame.draw.line(surface, GRAY, (sep_x, sep_y0), (sep_x, sep_y1), 2)

    left_mid = (block_x + sep_x) // 2
    right_mid = (sep_x + (block_x + block_w)) // 2

    group_w1 = ICON_SIZE + 10 + txt_temp.get_width()
    start_x1 = left_mid - group_w1 // 2
    surface.blit(icon_temp, (start_x1, content_top))
    surface.blit(txt_temp, (start_x1 + ICON_SIZE + 10, content_top + (ICON_SIZE - txt_temp.get_height()) // 2))

    group_w2 = ICON_SIZE + 10 + txt_humid.get_width()
    start_x2 = right_mid - group_w2 // 2
    surface.blit(icon_humid, (start_x2, content_top))
    surface.blit(txt_humid, (start_x2 + ICON_SIZE + 10, content_top + (ICON_SIZE - txt_humid.get_height()) // 2))

    # Prévisions 3 jours
    block_top = block_y + block_h + 50
    block_width = block_w
    block_height = HEIGHT - block_top - 20
    pygame.draw.rect(surface, WHITE, (block_x, block_top, block_width, block_height), border_radius=16)

    title2 = title_font.render("Prévisions 3 jours", True, BLACK)
    surface.blit(title2, (block_x + (block_width - title2.get_width()) // 2, block_top + 50))

    n = 3
    col_w = block_width // n

    for i in range(1, n + 1):
        x0 = block_x + (i - 1) * col_w
        cx = x0 + col_w // 2

        try:
            dt = datetime.fromisoformat(f["time"][i])
            date_str = dt.strftime("%a %d %b")
        except:
            date_str = f"Jour {i}"
        txt_date = date_font.render(date_str, True, DARK_BLUE)
        date_y = block_top + 180
        surface.blit(txt_date, (cx - txt_date.get_width() // 2, date_y))

        tp = "sunny"
        if f["precipitation_sum"][i] > 0:
            tp = "rainy"
        elif f["windspeed_10m_max"][i] > 20:
            tp = "windy"
        elif f["temperature_2m_max"][i] < 10:
            tp = "cloudy"
        icon = weather_icons[tp]
        icon_x = cx - icon.get_width() // 2
        icon_y = date_y + txt_date.get_height() + 20
        surface.blit(icon, (icon_x, icon_y))

        details = [
            f"{f['temperature_2m_max'][i]}° / {f['temperature_2m_min'][i]}°",
            f"Pluie : {f['precipitation_sum'][i]} mm",
            f"Vent : {f['windspeed_10m_max'][i]} km/h"
        ]
        detail_y0 = icon_y + icon.get_height() + 20
        for j, line_txt in enumerate(details):
            txt = detail_font.render(line_txt, True, BLACK)
            surface.blit(txt, (cx - txt.get_width() // 2, detail_y0 + j * (detail_font.get_height() + 8)))

    screen.blit(surface, (0, 0))
    draw_right_panel()

def page_vlille():
    """Page V'lille (partie gauche + panneau droit)"""
    vl = cache["vlille"]
    surface = pygame.Surface((LEFT_W, HEIGHT))
    surface.fill(DARK_RED)

    title_font = pygame.font.SysFont("Arial", 54, bold=True)
    subtitle_font = pygame.font.SysFont("Arial", 32)
    title = title_font.render("Station V'LILLE", True, WHITE)
    subtitle = subtitle_font.render(STATION_VLILLE, True, WHITE)

    surface.blit(title, ((LEFT_W - title.get_width()) // 2, 20))
    surface.blit(subtitle, ((LEFT_W - subtitle.get_width()) // 2, 20 + title.get_height() + 10))

    if not vl:
        err = font.render("Données V'LILLE indisponibles", True, WHITE)
        surface.blit(err, ((LEFT_W - err.get_width()) // 2, HEIGHT // 2))
        screen.blit(surface, (0, 0))
        draw_right_panel()
        return

    nbv, nbp = vl["nb_velos"], vl["nb_places"]
    total = nbv + nbp or 1
    pct_v, pct_p = nbv / total, nbp / total

    radius = min(LEFT_W, HEIGHT) // 5
    thickness = 28
    cy = HEIGHT // 2 - radius - 20 + 80
    gap = 20
    cx_center = LEFT_W // 2
    cx_v = cx_center - radius - gap // 2
    cx_p = cx_center + radius + gap // 2

    val_font = pygame.font.SysFont("Arial", 90, bold=True)
    lbl_font = pygame.font.SysFont("Arial", 70)

    def draw_circle(cx, pct, color, value, label):
        pygame.draw.circle(surface, GRAY, (cx, cy), radius)
        rect = pygame.Rect(cx - radius, cy - radius, 2 * radius, 2 * radius)
        deg2rad = 3.1416 / 180

        if label == "vélos":
            start_ang = (-90 - 360 * pct) * deg2rad
            end_ang = (-90) * deg2rad
        else:
            start_ang = (-90) * deg2rad
            end_ang = (-90 + 360 * pct) * deg2rad

        pygame.draw.arc(surface, color, rect, start_ang, end_ang, thickness)

        txt = val_font.render(str(value), True, BLACK)
        lbl = lbl_font.render(label, True, BLACK)
        surface.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2 - 10))
        surface.blit(lbl, (cx - lbl.get_width() // 2, cy + 20))

    draw_circle(cx_v, pct_v, DARK_BLUE, nbv, "vélos")
    draw_circle(cx_p, pct_p, GREEN, nbp, "places")

    # Logo V'lille - garder les proportions d'origine
    img = pygame.image.load("icons/vlille.png")
    img_w = int(LEFT_W * 0.55)
    img_h = int(img.get_height() * img_w / img.get_width())
    img = pygame.transform.smoothscale(img, (img_w, img_h))
    surface.blit(img, ((LEFT_W - img_w) // 2, HEIGHT - img_h - 20))

    screen.blit(surface, (0, 0))
    draw_right_panel()

# ==================== AFFICHAGE CONTENUS SERVEUR ====================

def display_image_fullscreen(filepath):
    """Affiche une image en plein écran"""
    try:
        image = pygame.image.load(filepath)
        image = pygame.transform.scale(image, (WIDTH, HEIGHT))
        screen.blit(image, (0, 0))
        pygame.display.flip()
        return True
    except Exception as e:
        print(f"❌ Erreur affichage image {filepath}: {e}")
        return False

def display_video_fullscreen(filepath, duration):
    """Affiche une vidéo en plein écran avec décodage optimisé"""
    try:
        cap = cv2.VideoCapture(filepath, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            print(f"❌ Impossible d'ouvrir la vidéo: {filepath}")
            return False

        cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)

        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0 or fps > 1000:
            fps = 30.0

        print(f"🎬 Lecture vidéo à {fps} FPS - Mode haute performance")

        total_duration_ms = int(duration * 1000)
        start_time = time.time()
        frame_duration = 1.0 / fps
        frame_count = 0

        while True:
            elapsed = (time.time() - start_time) * 1000
            if total_duration_ms > 0 and elapsed >= total_duration_ms:
                break

            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_count = 0
                start_time = time.time()
                continue

            frame = cv2.resize(frame, (WIDTH, HEIGHT), interpolation=cv2.INTER_NEAREST)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))

            screen.blit(surf, (0, 0))
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    cap.release()
                    return False
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        cap.release()
                        return False

            frame_count += 1
            target_time = start_time + (frame_count * frame_duration)
            sleep_time = target_time - time.time()

            if sleep_time > 0:
                time.sleep(sleep_time)

        cap.release()
        return True

    except Exception as e:
        print(f"❌ Erreur affichage vidéo {filepath}: {e}")
        try:
            cap.release()
        except:
            pass
        return False

# ==================== BOUCLE PRINCIPALE ====================

def main():
    """Boucle principale d'affichage"""
    print("🚀 Démarrage de l'affichage dynamique JUNIA - Version combinée")
    
    # Initialiser gestionnaire de contenus serveur
    content_manager = ContentManager()
    
    # Test connexion serveur
    if not content_manager.test_server_connection():
        print("⚠️  Impossible de se connecter au serveur (contenus serveur désactivés)")
    
    # Synchronisation initiale
    content_manager.sync_contents()
    content_manager.start_sync_thread()
    
    # Mise à jour données API
    update_all_api_data()
    
    # Timer pour mise à jour API (toutes les 60s)
    UPDATE_EVENT = pygame.USEREVENT + 1
    pygame.time.set_timer(UPDATE_EVENT, 60000)
    
    # Pages API
    api_pages = [
        ("bus", page_bus, API_PAGE_DURATION),
        ("weather", page_weather, API_PAGE_DURATION),
        ("vlille", page_vlille, API_PAGE_DURATION)
    ]
    
    current_page_index = 0
    page_start_time = time.time()
    last_content_check = 0
    
    running = True
    
    while running:
        current_time = time.time()
        
        # Gestion des événements
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_SPACE:
                    print("🔄 Synchronisation manuelle...")
                    content_manager.sync_contents()
                    update_all_api_data()
                elif event.key == pygame.K_RIGHT:
                    # Forcer passage à la page suivante
                    page_start_time = 0
            elif event.type == UPDATE_EVENT:
                update_all_api_data()
        
        # Vérifier mise à jour contenus serveur (toutes les 30s)
        if current_time - last_content_check > 30:
            media_contents = content_manager.get_available_contents()
            last_content_check = current_time
            if media_contents:
                print(f"📋 {len(media_contents)} contenus média disponibles")
        
        # Construire liste complète des pages (API + contenus serveur)
        all_pages = list(api_pages)
        
        # Ajouter contenus serveur à la rotation
        media_contents = content_manager.get_available_contents()
        for content in media_contents:
            all_pages.append(("media", content, content['duration']))
        
        if not all_pages:
            # Aucune page disponible
            screen.fill(BLACK)
            err = font.render("Aucun contenu disponible", True, WHITE)
            screen.blit(err, ((WIDTH - err.get_width()) // 2, HEIGHT // 2))
            pygame.display.flip()
            time.sleep(1)
            continue
        
        # Gérer changement de page
        current_page_type, current_page_data, duration = all_pages[current_page_index % len(all_pages)]
        
        if current_time - page_start_time >= duration:
            # Passer à la page suivante
            current_page_index = (current_page_index + 1) % len(all_pages)
            page_start_time = current_time
            current_page_type, current_page_data, duration = all_pages[current_page_index]
            
            print(f"📄 Page {current_page_index + 1}/{len(all_pages)}: {current_page_type}")
        
        # Afficher la page actuelle
        if current_page_type in ["bus", "weather", "vlille"]:
            # Page API (avec panneau droit)
            current_page_data()  # C'est une fonction
        
        elif current_page_type == "media":
            # Contenu serveur (plein écran)
            content = current_page_data  # C'est un dict
            
            if content['type'] == 'image':
                display_image_fullscreen(content['filepath'])
            
            elif content['type'] == 'video':
                success = display_video_fullscreen(content['filepath'], content['duration'])
                if success:
                    # Vidéo terminée normalement, passer à la suivante
                    current_page_index = (current_page_index + 1) % len(all_pages)
                    page_start_time = current_time
                else:
                    # Erreur ou interruption, passer à la suivante
                    current_page_index = (current_page_index + 1) % len(all_pages)
                    page_start_time = current_time
        
        pygame.display.flip()
        clock.tick(30)
    
    # Nettoyage
    content_manager.stop()
    pygame.quit()
    print("👋 Affichage arrêté")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
