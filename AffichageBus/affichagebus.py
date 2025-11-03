import pygame
import requests
import sys
import time
import os
import cv2
from datetime import datetime, timedelta
import subprocess

# ----------------- CONFIG -----------------
API_URL    = "https://data.lillemetropole.fr/data/ogcapi/collections/ilevia:prochains_passages/items?f=json&limit=-1"
VLILLE_URL = "https://data.lillemetropole.fr/geoserver/wfs?SERVICE=WFS&REQUEST=GetFeature&VERSION=2.0.0&TYPENAMES=dsp_ilevia%3Avlille_temps_reel&OUTPUTFORMAT=application%2Fjson"
METEO_URL  = "https://api.open-meteo.com/v1/forecast?latitude=50.6333&longitude=3.0667&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,weather_code&current_weather=true&timezone=Europe/Paris"
ACTUAL_URL  = "https://api.open-meteo.com/v1/forecast?latitude=50.633&longitude=3.0586&models=meteofrance_seamless&current=temperature_2m,relative_humidity_2m&forecast_days=1"

NOM_STATION    = "SOLFERINO"
STATION_VLILLE = "PALAIS RAMEAU"

# Durées d'affichage
BASE_DURATIONS = [10, 10, 10]   # pages normales
MEDIA_DURATION = 20             # secondes pour chaque image/vidéo

# Dossier des médias
MEDIA_DIR = "icons"
MEDIA_FILES = [
    "img1.mp4", "img (2).png", "img (3).png", "img (4).png",
    "img (5).png", "img (6).png", "img (7).png", "img (8).png",
    "img (9).png", "img (10).png"
]

# ----------------- PYGAME INIT -----------------
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.mouse.set_visible(False)
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h

LEFT_W  = WIDTH * 2 // 3
RIGHT_W = WIDTH - LEFT_W
LEFT_RECT  = pygame.Rect(0, 0, LEFT_W, HEIGHT)
RIGHT_RECT = pygame.Rect(LEFT_W, 0, RIGHT_W, HEIGHT)

font       = pygame.font.Font(None, 60)
small_font = pygame.font.Font(None, 50)
meteopanel_font = pygame.font.Font(None, 70)

WHITE      = (255,255,255)
BLACK      = (  0,  0,  0)
BLUE       = (  0,102,204)
GREEN      = (  0,153,  0)
RED        = (255,  0,  0)
GRAY       = (200,200,200)
DARK_RED   = (139,  0,  0)
LIGHT_BLUE = (173,216,230)
DARK_BLUE  = ( 70,130,180)
ORANGE     = (252,93,51)
PURPLE     = (63,42,85)

# Directions des lignes de bus
DIRECTIONS = {
    "L5": ["MARCQ FERME AUX OIES", "HAUBOURDIN LE PARC"],
    "18": ["LOMME ANATOLE FRANCE", "VILLENEUVE D'ASCQ HOTEL DE VILLE"]
}

# Icônes météo
weather_icons = {
    "sunny" : pygame.image.load("icons/sunny.png"),
    "cloudy": pygame.image.load("icons/cloudy.png"),
    "rainy" : pygame.image.load("icons/rainy.png"),
    "windy" : pygame.image.load("icons/windy.png")
}

# ----------------- CACHE -----------------
cache = {
    "actual": {},
    "forecast": None,
    "vlille": None,
    "bus_next": {},
    "bus_records": [],
    "last_update": None,
    "last_error": None
}

# ----------------- DATA FETCH -----------------
def fetch_actual():
    try:
        r = requests.get(ACTUAL_URL, timeout=5); r.raise_for_status()
        d = r.json()
        current = d.get("current", {})
        cache["actual"]["temperature"] = current.get("temperature_2m", cache["actual"].get("temperature"))
        cache["actual"]["humidity"]    = current.get("relative_humidity_2m", cache["actual"].get("humidity"))
        cache["last_error"] = None
    except Exception as e:
        cache["last_error"] = f"Actuelle : {e}"
    return cache["actual"]

def fetch_forecast():
    try:
        r = requests.get(METEO_URL, timeout=10); r.raise_for_status()
        cache["forecast"] = r.json()["daily"]
        cache["last_error"] = None
    except Exception as e:
        cache["last_error"] = f"Météo: {e}"
    return cache["forecast"]

def fetch_vlille():
    try:
        r = requests.get(VLILLE_URL, timeout=10); r.raise_for_status()
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
    try:
        r = requests.get(API_URL, timeout=10); r.raise_for_status()
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
                        if dt.tzinfo: dt = dt.replace(tzinfo=None)
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

def update_all_data():
    fetch_actual()
    fetch_vlille()
    fetch_bus_next()
    fetch_forecast()
    cache["last_update"] = datetime.now()

# ----------------- PAGES D'AFFICHAGE -----------------

def draw_right_panel():
    pygame.draw.rect(screen, PURPLE, RIGHT_RECT)
    x0 = LEFT_W + 20

    # Horloge
    time_font = pygame.font.Font(None, 250)
    time_str  = datetime.now().strftime("%H:%M")
    time_surf = time_font.render(time_str, True, ORANGE)
    time_x    = LEFT_W + (RIGHT_W - time_surf.get_width()) // 2
    screen.blit(time_surf, (time_x, 50))

    title_font = pygame.font.Font(None, 60)
    value_font = pygame.font.Font(None, 50)

    # Bloc météo actuelle
    actual = cache["actual"]
    block_x, block_y = x0, 250
    block_w, block_h = RIGHT_W - 40, 200
    pygame.draw.rect(screen, WHITE, (block_x, block_y, block_w, block_h), border_radius=12)

    title_txt = title_font.render("Météo actuelle", True, BLACK)
    title_x   = block_x + (block_w - title_txt.get_width()) // 2
    screen.blit(title_txt, (title_x, block_y + 25))

    content_top = block_y + 10 + title_txt.get_height() + 30

    ICON_SIZE = 100
    icon_temp  = pygame.transform.smoothscale(pygame.image.load("icons/temp.png"), (ICON_SIZE, ICON_SIZE))
    icon_humid = pygame.transform.smoothscale(pygame.image.load("icons/humidity.png"), (ICON_SIZE, ICON_SIZE))
    t = actual.get("temperature", "--")
    h = actual.get("humidity", "--")
    txt_temp  = meteopanel_font.render(f"{t}°C", True, BLACK)
    txt_humid = meteopanel_font.render(f"{h}%",  True, BLACK)

    sep_x = block_x + block_w // 2 + 20
    sep_y0 = block_y + 25 + title_txt.get_height() + 10
    sep_y1 = block_y + block_h - 25
    pygame.draw.line(screen, GRAY, (sep_x, sep_y0), (sep_x, sep_y1), 2)

    left_mid  = block_x + block_w // 4
    right_mid = block_x + 3 * block_w // 4

    group_w1 = ICON_SIZE + 10 + txt_temp.get_width()
    start_x1 = left_mid - group_w1 // 2
    y_icon = content_top
    y_text = y_icon + (ICON_SIZE - txt_temp.get_height()) // 2
    screen.blit(icon_temp, (start_x1, y_icon))
    screen.blit(txt_temp,  (start_x1 + ICON_SIZE + 10, y_text))

    group_w2 = ICON_SIZE + 10 + txt_humid.get_width()
    start_x2 = right_mid - group_w2 // 2
    screen.blit(icon_humid, (start_x2, y_icon))
    screen.blit(txt_humid,  (start_x2 + ICON_SIZE + 10, y_text))

    # Bloc V'Lille
    vlille_block = pygame.Rect(x0, block_y + block_h + 20, block_w, 180)
    pygame.draw.rect(screen, WHITE, vlille_block, border_radius=12)

    title2 = font.render(f"V'Lille – {STATION_VLILLE}", True, BLACK)
    title2_x = vlille_block.x + (vlille_block.w - title2.get_width()) // 2
    screen.blit(title2, (title2_x, vlille_block.y + 25))

    vl = cache["vlille"] or {"nb_velos":0,"nb_places":0}
    nbv, nbp = vl["nb_velos"], vl["nb_places"]
    total = nbv + nbp or 1
    pct_v = nbv / total
    bar_x = vlille_block.x + 10
    bar_y = vlille_block.y + 95
    bar_w = vlille_block.w - 20
    bar_h = 24
    red_w = int(bar_w * pct_v)
    green_w = bar_w - red_w
    pygame.draw.rect(screen, DARK_BLUE,   (bar_x, bar_y, red_w, bar_h), border_radius=8)
    pygame.draw.rect(screen, GREEN, (bar_x + red_w, bar_y, green_w, bar_h), border_radius=8)

    nbv_txt = small_font.render(f"{nbv} vélos", True, BLACK)
    nbp_txt = small_font.render(f"{nbp} places", True, BLACK)

    nbv_x = bar_x + 5
    nbp_x = bar_x + bar_w - nbp_txt.get_width() - 5

    screen.blit(nbv_txt, (nbv_x, bar_y + bar_h + 8))
    screen.blit(nbp_txt, (nbp_x, bar_y + bar_h + 8))

    # Bloc bus
    bus_block = pygame.Rect(x0, vlille_block.y + vlille_block.h + 20, block_w, 200)
    pygame.draw.rect(screen, WHITE, bus_block, border_radius=12)

    title3 = font.render("Prochains bus – Solférino", True, BLACK)
    title3_x = bus_block.x + (bus_block.w - title3.get_width()) // 2
    screen.blit(title3, (title3_x, bus_block.y + 25))

    now_dt = datetime.now()
    yy = bus_block.y + 85

    nxt = cache["bus_next"]

    now_min = now_dt.replace(second=0, microsecond=0)

    for line, col in [("L5", BLUE), ("18", GREEN)]:
        dt = nxt.get(line)
        if dt:
            delta_min = (dt.hour*60 + dt.minute) - (now_min.hour*60 + now_min.minute)
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


def page_bus():
    recs = cache.get("bus_records", [])

    surf = pygame.Surface((WIDTH, HEIGHT))
    surf.fill(WHITE)

    direction_font = pygame.font.Font(None, 35)

    # Titre
    title_txt = font.render("Bus Ilévia - Arrêt Solférino", True, BLACK)
    title_x = (surf.get_width() - title_txt.get_width()) // 2
    title_y = 20
    surf.blit(title_txt, (title_x, title_y))
    y = 80
    now = datetime.now()

    ICON_SIZE = 40
    icons = {}
    for line in ["L5", "18"]:
        icons[line] = {
            "aller": pygame.transform.smoothscale(
                pygame.image.load(f"icons/bus{line}aller.png"),
                (int(ICON_SIZE*2.5), ICON_SIZE)
            ),
            "retour": pygame.transform.smoothscale(
                pygame.image.load(f"icons/bus{line}retour.png"),
                (int(ICON_SIZE*2.5), ICON_SIZE)
            ),
        }

    for line, color in [("L5", BLUE), ("18", GREEN)]:
        # Nom de ligne
        surf.blit(font.render(line, True, color), (20, y))
        y += 70

        # Deux sens
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
                        if dt.tzinfo: dt = dt.replace(tzinfo=None)
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

                surf.blit(
                    small_font.render(f"{tm}   {delay_str}", True, BLACK),
                    (60, y)
                )
                y += 50

            y += 10
        y += 45

        # Frise chronologique
        margin = 100
        frise_w = WIDTH - 2 * margin
        y0 = y

        surf.blit(direction_font.render(DIRECTIONS[line][0], True, BLACK),
                  (margin, y0 - 40))
        end_lbl = direction_font.render(DIRECTIONS[line][1], True, BLACK)
        surf.blit(end_lbl, (margin + frise_w - end_lbl.get_width(), y0 - 40))

        pygame.draw.line(surf, BLACK, (margin, y0), (margin + frise_w, y0), 4)

        for delta, text in [(-20, "20m"), (-10, "10m"), (-5, "5m"),
                            (0, "JUNIA"), (5, "5m"), (10, "10m"), (20, "20m")]:
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

        # Icônes bus sur la frise
        dir_next = {}
        for sens in DIRECTIONS[line]:
            times = []
            for it in recs:
                if (it.get("code_ligne") == line
                        and it.get("sens_ligne") == sens
                        and it.get("nom_station") == NOM_STATION):
                    try:
                        dt = datetime.fromisoformat(it["heure_estimee_depart"])
                        if dt.tzinfo: dt = dt.replace(tzinfo=None)
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
                    icon = icons[line]["aller"]
                else:
                    x = margin + (dm + 20) * frise_w // 40
                    icon = icons[line]["retour"]
                y_icon = y0 - ICON_SIZE // 2
                surf.blit(icon, (x - ICON_SIZE // 2, y_icon))
        y += 70

    screen.blit(surf, (0, 0))



def page_vlille():
    vl = cache["vlille"]
    surface = pygame.Surface((WIDTH, HEIGHT))
    surface.fill(DARK_RED)

    # Titres
    title_font = pygame.font.SysFont("Arial", 54, bold=True)
    subtitle_font = pygame.font.SysFont("Arial", 32)
    title = title_font.render("Station V'LILLE", True, WHITE)
    subtitle = subtitle_font.render(STATION_VLILLE, True, WHITE)

    surface.blit(title, ((WIDTH - title.get_width()) // 2, 20))
    surface.blit(subtitle, ((WIDTH - subtitle.get_width()) // 2, 20 + title.get_height() + 10))

    if not vl:
        err = font.render("Données V'LILLE indisponibles", True, WHITE)
        surface.blit(err, ((WIDTH - err.get_width()) // 2, HEIGHT // 2))
        screen.blit(surface, (0, 0))
        return

    nbv, nbp = vl["nb_velos"], vl["nb_places"]
    total = nbv + nbp or 1
    pct_v, pct_p = nbv / total, nbp / total

    # Cercles vélos / places
    radius = min(WIDTH, HEIGHT) // 5
    thickness = 28
    cy = HEIGHT // 2 - radius - 20 + 80
    gap = 20
    cx_center = WIDTH // 2
    cx_v = cx_center - radius - gap // 2
    cx_p = cx_center + radius + gap // 2

    val_font = pygame.font.SysFont("Arial", 90, bold=True)
    lbl_font = pygame.font.SysFont("Arial", 70)

    prev_v = cache["vlille"].get("prev_pct_v", pct_v)
    prev_p = cache["vlille"].get("prev_pct_p", pct_p)
    steps = 10
    for step in range(1, steps + 1):
        frac = step / steps
        cur_v = prev_v + (pct_v - prev_v) * frac
        cur_p = prev_p + (pct_p - prev_p) * frac

        surface.fill(DARK_RED)
        surface.blit(title, ((WIDTH - title.get_width()) // 2, 20))
        surface.blit(subtitle, ((WIDTH - subtitle.get_width()) // 2, 20 + title.get_height() + 10))

        def draw_circle(cx, pct, color, value, label):
            pygame.draw.circle(surface, GRAY, (cx, cy), radius)
            rect = pygame.Rect(cx - radius, cy - radius, 2 * radius, 2 * radius)
            deg2rad = 3.1416 / 180

            if label == "vélos":
                start_ang = (-90 - 360 * pct) * deg2rad
                end_ang   = (-90) * deg2rad
            else:
                start_ang = (-90) * deg2rad
                end_ang   = (-90 + 360 * pct) * deg2rad

            pygame.draw.arc(surface, color, rect, start_ang, end_ang, thickness)

            txt = val_font.render(str(value), True, BLACK)
            lbl = lbl_font.render(label, True, BLACK)
            surface.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2 - 10))
            surface.blit(lbl, (cx - lbl.get_width() // 2, cy + 20))

        draw_circle(cx_v, cur_v, DARK_BLUE, nbv, "vélos")
        draw_circle(cx_p, cur_p, GREEN, nbp, "places")

        # Logo V'Lille
        img = pygame.image.load("icons/vlille.png")
        img_w = int(WIDTH * 0.55)
        img_h = int(img.get_height() * img_w / img.get_width())
        img = pygame.transform.smoothscale(img, (img_w, img_h))
        surface.blit(img, ((WIDTH - img_w) // 2, HEIGHT - img_h - 20))

        screen.blit(surface, (0, 0))
        pygame.display.flip()
        pygame.time.delay(30)

    cache["vlille"]["prev_pct_v"] = pct_v
    cache["vlille"]["prev_pct_p"] = pct_p

    screen.blit(surface, (0, 0))


def page_right_panel():
    """Ancien panneau droit, maintenant une page plein écran avec infos en 2 colonnes"""
    screen.fill(PURPLE)

    # ----------- Heure en haut -----------
    time_font = pygame.font.Font(None, 180)
    time_str  = datetime.now().strftime("%H:%M")
    time_surf = time_font.render(time_str, True, ORANGE)
    time_x    = (WIDTH - time_surf.get_width()) // 2
    screen.blit(time_surf, (time_x, 40))

    # ----------- Préparation colonnes -----------
    margin = 50
    col_w = (WIDTH - 3*margin) // 2
    col_h = (HEIGHT - 240) // 2   # un peu plus petit
    start_y = 220

    title_font = pygame.font.Font(None, 60)
    value_font = pygame.font.Font(None, 45)

    # ----------- Bloc météo (colonne gauche, ligne 1) -----------
    actual = cache["actual"]
    rect_meteo = pygame.Rect(margin, start_y, col_w, col_h)
    pygame.draw.rect(screen, WHITE, rect_meteo, border_radius=16)

    title = title_font.render("Météo", True, BLACK)
    screen.blit(title, (rect_meteo.centerx - title.get_width()//2, rect_meteo.y + 15))

    t = actual.get("temperature", "--")
    h = actual.get("humidity", "--")

    icon_temp  = pygame.transform.smoothscale(pygame.image.load("icons/temp.png"), (100, 100))
    icon_humid = pygame.transform.smoothscale(pygame.image.load("icons/humidity.png"), (100, 100))

    txt_temp  = value_font.render(f"{t}°C", True, BLACK)
    txt_humid = value_font.render(f"{h}%", True, BLACK)

    screen.blit(icon_temp, (rect_meteo.x + 40, rect_meteo.y + 90))
    screen.blit(txt_temp,  (rect_meteo.x + 120, rect_meteo.y + 100))

    screen.blit(icon_humid, (rect_meteo.x + 40, rect_meteo.y + 170))
    screen.blit(txt_humid,  (rect_meteo.x + 120, rect_meteo.y + 180))

    # ----------- Bloc V'Lille (colonne droite, ligne 1) -----------
    vl = cache["vlille"] or {"nb_velos": 0, "nb_places": 0}
    nbv, nbp = vl["nb_velos"], vl["nb_places"]

    rect_vlille = pygame.Rect(margin*2 + col_w, start_y, col_w, col_h)
    pygame.draw.rect(screen, WHITE, rect_vlille, border_radius=16)

    title = title_font.render("V'Lille", True, BLACK)
    screen.blit(title, (rect_vlille.centerx - title.get_width()//2, rect_vlille.y + 15))

    txt_v = value_font.render(f"{nbv} vélos", True, BLACK)
    txt_p = value_font.render(f"{nbp} places", True, BLACK)
    screen.blit(txt_v, (rect_vlille.centerx - txt_v.get_width()//2, rect_vlille.y + 110))
    screen.blit(txt_p, (rect_vlille.centerx - txt_p.get_width()//2, rect_vlille.y + 170))

    # ----------- Bloc Bus L5 (colonne gauche, ligne 2) -----------
    nxt = cache["bus_next"]
    rect_bus = pygame.Rect(margin, start_y + col_h + margin, col_w, col_h)
    pygame.draw.rect(screen, WHITE, rect_bus, border_radius=16)

    title = title_font.render("Bus L5", True, BLUE)
    screen.blit(title, (rect_bus.centerx - title.get_width()//2, rect_bus.y + 15))

    dt = nxt.get("L5")
    delay = "--:--"
    if dt:
        now = datetime.now()
        delta_min = (dt - now).total_seconds() // 60
        delay = "imminent" if delta_min <= 0 else f"{int(delta_min)} min"
    txt = value_font.render(f"Prochain : {delay}", True, BLACK)
    screen.blit(txt, (rect_bus.centerx - txt.get_width()//2, rect_bus.y + 120))

    # ----------- Bloc Bus 18 (colonne droite, ligne 2) -----------
    rect_bus2 = pygame.Rect(margin*2 + col_w, start_y + col_h + margin, col_w, col_h)
    pygame.draw.rect(screen, WHITE, rect_bus2, border_radius=16)

    title = title_font.render("Bus 18", True, GREEN)
    screen.blit(title, (rect_bus2.centerx - title.get_width()//2, rect_bus2.y + 15))

    dt = nxt.get("18")
    delay = "--:--"
    if dt:
        now = datetime.now()
        delta_min = (dt - now).total_seconds() // 60
        delay = "imminent" if delta_min <= 0 else f"{int(delta_min)} min"
    txt = value_font.render(f"Prochain : {delay}", True, BLACK)
    screen.blit(txt, (rect_bus2.centerx - txt.get_width()//2, rect_bus2.y + 120))


def page_weather():
    f = cache["forecast"]
    surface = pygame.Surface((WIDTH, HEIGHT))
    surface.fill(LIGHT_BLUE)

    # Titre principal
    title_font = pygame.font.Font(None, 90)
    value_font = pygame.font.Font(None, 150)
    date_font = pygame.font.Font(None, 70)
    detail_font = pygame.font.Font(None, 60)

    block_x, block_y = 20, 20
    block_w = WIDTH - 40
    block_h = 370
    pygame.draw.rect(surface, WHITE, (block_x, block_y, block_w, block_h), border_radius=16)

    title_txt = title_font.render("Météo actuelle", True, BLACK)
    title_x = block_x + (block_w - title_txt.get_width()) // 2
    title_y = block_y + 30
    surface.blit(title_txt, (title_x, title_y))

    if f is None:
        err = font.render("Données météo indisponibles", True, RED)
        surface.blit(err, ((WIDTH - err.get_width()) // 2, HEIGHT // 2))
        screen.blit(surface, (0, 0))
        return

    # Données actuelles (température + humidité)
    content_top = title_y + title_txt.get_height() + 50

    ICON_SIZE = 200
    icon_temp = pygame.transform.smoothscale(pygame.image.load("icons/temp.png"), (ICON_SIZE, ICON_SIZE))
    icon_humid = pygame.transform.smoothscale(pygame.image.load("icons/humidity.png"), (ICON_SIZE, ICON_SIZE))

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
    surface.blit(txt_temp, (start_x1 + ICON_SIZE + 10,
                             content_top + (ICON_SIZE - txt_temp.get_height()) // 2))

    group_w2 = ICON_SIZE + 10 + txt_humid.get_width()
    start_x2 = right_mid - group_w2 // 2
    surface.blit(icon_humid, (start_x2, content_top))
    surface.blit(txt_humid, (start_x2 + ICON_SIZE + 10,
                              content_top + (ICON_SIZE - txt_humid.get_height()) // 2))

    # Bloc prévisions sur 3 jours
    block_top = block_y + block_h + 50
    block_width = block_w
    block_height = HEIGHT - block_top - 20
    pygame.draw.rect(surface, WHITE,
                     (block_x, block_top, block_width, block_height),
                     border_radius=16)

    title2 = title_font.render("Prévisions 3 jours", True, BLACK)
    surface.blit(
        title2,
        (block_x + (block_width - title2.get_width()) // 2, block_top + 50)
    )

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
        surface.blit(txt_date,
                     (cx - txt_date.get_width() // 2, date_y))

        # Choix de l'icône météo
        tp = "sunny"
        if f["precipitation_sum"][i] > 0:
            tp = "rainy"
        elif f["windspeed_10m_max"][i] > 20:
            tp = "windy"
        elif f["temperature_2m_max"][i] < 10:
            tp = "cloudy"
        icon = pygame.transform.scale(weather_icons[tp], (150, 150))
        icon_x = cx - icon.get_width() // 2
        icon_y = date_y + txt_date.get_height() + 20
        surface.blit(icon, (icon_x, icon_y))

        # Détails des prévisions
        details = [
            f"{f['temperature_2m_max'][i]}° / {f['temperature_2m_min'][i]}°",
            f"Pluie : {f['precipitation_sum'][i]} mm",
            f"Vent : {f['windspeed_10m_max'][i]} km/h"
        ]
        detail_y0 = icon_y + icon.get_height() + 20
        for j, line_txt in enumerate(details):
            txt = detail_font.render(line_txt, True, BLACK)
            surface.blit(txt,
                         (cx - txt.get_width() // 2,
                          detail_y0 + j * (detail_font.get_height() + 8)))

    screen.blit(surface, (0, 0))


# ----------------- PAGES MÉDIAS -----------------

def page_media_image(path):
    """Affiche une image en plein écran sur la partie gauche avec transition en fondu entrée/sortie"""
    surf = pygame.Surface((WIDTH, HEIGHT))
    surf.fill(BLACK)
    try:
        img = pygame.image.load(os.path.join(MEDIA_DIR, path))
        img = pygame.transform.smoothscale(img, (WIDTH, HEIGHT))
        img = img.convert_alpha()

        # --- Fondu d'entrée ---
        for alpha in range(0, 256, 15):  # 15 = vitesse du fondu
            temp = img.copy()
            temp.set_alpha(alpha)
            surf.fill(BLACK)
            surf.blit(temp, (0, 0))
            screen.blit(surf, (0, 0))

            #draw_right_panel()
            pygame.display.flip()
            pygame.time.delay(30)

        # --- Maintien de l'image (durée moins temps de fondu) ---
        start_time = time.time()
        while time.time() - start_time < MEDIA_DURATION - 1:  # on laisse 1s pour le fondu sortie
            surf.fill(BLACK)
            surf.blit(img, (0, 0))
            screen.blit(surf, (0, 0))
            #draw_right_panel()
            pygame.display.flip()
            pygame.time.delay(100)

        # --- Fondu de sortie ---
        for alpha in range(255, -1, -15):
            temp = img.copy()
            temp.set_alpha(alpha)
            surf.fill(BLACK)
            surf.blit(temp, (0, 0))
            screen.blit(surf, (0, 0))

            #draw_right_panel()
            pygame.display.flip()
            pygame.time.delay(30)

    except Exception as e:
        err = font.render(f"Erreur : {e}", True, RED)
        surf.blit(err, (20, HEIGHT//2))
        screen.blit(surf, (0, 0))


def page_media_video(path):
    """Lit une vidéo mp4 et l'affiche en plein écran à sa vitesse normale"""
    video_path = os.path.join(MEDIA_DIR, path)
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        err = font.render("Impossible de lire la vidéo", True, RED)
        screen.blit(err, (20, HEIGHT//2))
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 25  # fps par défaut si non dispo
    frame_delay = int(1000 / fps)          # délai entre chaque frame en ms

    start_time = time.time()
    while time.time() - start_time < MEDIA_DURATION:
        ret, frame = cap.read()
        if not ret:
            break  # fin de vidéo → on sort

        frame = cv2.resize(frame, (WIDTH, HEIGHT))  # plein écran total
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0,1))
        screen.blit(frame_surface, (0, 0))

        pygame.display.flip()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()

        pygame.time.delay(frame_delay)  # respect du rythme vidéo

    cap.release()


# ----------------- MAIN -----------------

def main():
    # Pages info + panneau droit
    pages = [page_bus, page_weather, page_vlille, page_right_panel]
    durations = BASE_DURATIONS + [10]   # ex: [10, 10, 10] + [10] = 4 durées

    # Ajout médias
    for f in MEDIA_FILES:
        if f.endswith(".mp4"):
            pages.append(lambda f=f: page_media_video(f))
        else:
            pages.append(lambda f=f: page_media_image(f))
        durations.append(MEDIA_DURATION)   # ajoute la durée correspondante

    # Vérif de cohérence
    if len(pages) != len(durations):
        print(f"[ERREUR] {len(pages)} pages mais {len(durations)} durées")
        return

    idx, t0 = 0, time.time()
    clock = pygame.time.Clock()
    update_all_data()

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()

        # Rotation après la durée prévue
        if time.time() - t0 > durations[idx]:
            idx = (idx + 1) % len(pages)
            t0 = time.time()

        screen.fill(BLACK)

        try:
            # Exécuter la page courante
            pages[idx]()
        except Exception as e:
            print(f"[ERREUR] Page {idx} a échoué: {e}")
            # On saute cette page et on passe à la suivante
            idx = (idx + 1) % len(pages)
            t0 = time.time()
            continue

        pygame.display.flip()
        clock.tick(15)

if __name__ == "__main__":
    main()

