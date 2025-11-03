#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Client Raspberry Pi - Affichage Dynamique JUNIA
Synchronisation et affichage des contenus depuis le serveur
"""

import os
import sys
import time
import json
import requests
import pygame
import cv2
from threading import Thread
from datetime import datetime

# Configuration du serveur
#SERVER_URL = "http://192.168.1.26:8090"
#SERVER_URL = "http://10.224.0.123:8090"
#SERVER_URL = "http://affichage.junia.local:8090"
SERVER_URL = "http://192.168.1.20:8090"
CONTENT_SYNC_INTERVAL = 60  # Synchronisation toutes les 60 secondes
BASE_DURATIONS = [10, 10, 10]  # Durées bus, météo, v'lille en secondes
MEDIA_DURATION_DEFAULT = 20

# Dossiers
DOWNLOADS_FOLDER = "downloads"
CACHE_FOLDER = "cache"

# Créer les dossiers nécessaires
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
os.makedirs(CACHE_FOLDER, exist_ok=True)

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
                data = response.json()
                print(f"✅ Serveur connecté: {data.get('message', 'OK')}")
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
            
            # Récupérer la liste des contenus
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
                
                # Télécharger si le fichier n'existe pas
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
            
            # Mettre à jour la liste des contenus
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
                # Vérifier les dates de planification si définies
                now = datetime.now()
                
                if content.get('start_date'):
                    start_date = datetime.fromisoformat(content['start_date'])
                    if now < start_date:
                        continue  # Pas encore actif
                
                if content.get('end_date'):
                    end_date = datetime.fromisoformat(content['end_date'])
                    if now > end_date:
                        continue  # Expiré
                
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

class AffichageBusWithServer:
    """Classe principale d'affichage avec serveur"""
    
    def __init__(self):
        self.content_manager = ContentManager()
        self.current_page = 0
        self.last_content_check = 0
        self.media_contents = []
        
        # Initialisation Pygame
        pygame.init()
        
        # Configuration plein écran
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.screen_width, self.screen_height = self.screen.get_size()
        
        pygame.display.set_caption("Affichage Bus JUNIA - Serveur")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.big_font = pygame.font.Font(None, 72)
        
        print(f"🖥️  Affichage initialisé: {self.screen_width}x{self.screen_height}")
    
    def show_waiting_screen(self):
        """Affiche un écran d'attente quand aucun contenu n'est disponible"""
        self.screen.fill((0, 50, 100))  # Bleu foncé
        
        # Message principal
        title_surface = self.big_font.render("JUNIA ISEN", True, (255, 255, 255))
        title_rect = title_surface.get_rect(center=(self.screen_width//2, self.screen_height//2 - 50))
        self.screen.blit(title_surface, title_rect)
        
        # Message d'attente
        wait_surface = self.font.render("En attente de contenus...", True, (200, 200, 200))
        wait_rect = wait_surface.get_rect(center=(self.screen_width//2, self.screen_height//2 + 50))
        self.screen.blit(wait_surface, wait_rect)
        
        # Heure
        current_time = datetime.now().strftime("%H:%M:%S")
        time_surface = self.font.render(current_time, True, (150, 150, 150))
        time_rect = time_surface.get_rect(bottomright=(self.screen_width-20, self.screen_height-20))
        self.screen.blit(time_surface, time_rect)
        
        pygame.display.flip()
    
    def display_text_page(self, page_data):
        """Affiche une page de texte"""
        self.screen.fill((0, 50, 100))  # Bleu foncé
        
        # Titre
        title_surface = self.big_font.render(page_data['title'], True, (255, 255, 255))
        title_rect = title_surface.get_rect(center=(self.screen_width//2, 100))
        self.screen.blit(title_surface, title_rect)
        
        # Contenu
        content_surface = self.font.render(page_data['content'], True, (200, 200, 200))
        content_rect = content_surface.get_rect(center=(self.screen_width//2, 200))
        self.screen.blit(content_surface, content_rect)
        
        # Logo JUNIA (simulé)
        logo_text = self.font.render("JUNIA ISEN", True, (255, 255, 255))
        logo_rect = logo_text.get_rect(bottomright=(self.screen_width-20, self.screen_height-20))
        self.screen.blit(logo_text, logo_rect)
        
        pygame.display.flip()
    
    def display_image(self, filepath):
        """Affiche une image"""
        try:
            image = pygame.image.load(filepath)
            # Redimensionner pour s'adapter à l'écran
            image = pygame.transform.scale(image, (self.screen_width, self.screen_height))
            self.screen.blit(image, (0, 0))
            pygame.display.flip()
            return True
        except Exception as e:
            print(f"❌ Erreur affichage image {filepath}: {e}")
            return False
    
    def display_video(self, filepath, duration):
        """Affiche une vidéo"""
        try:
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                print(f"❌ Impossible d'ouvrir la vidéo: {filepath}")
                return False
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 25  # FPS par défaut
            
            frame_time = 1000 / fps  # Temps par frame en ms
            start_time = pygame.time.get_ticks()
            
            while pygame.time.get_ticks() - start_time < duration * 1000:
                ret, frame = cap.read()
                if not ret:
                    # Recommencer la vidéo
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                
                # Convertir OpenCV -> Pygame
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (self.screen_width, self.screen_height))
                frame = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
                
                self.screen.blit(frame, (0, 0))
                pygame.display.flip()
                
                # Contrôler le timing
                pygame.time.wait(int(frame_time))
                
                # Vérifier les événements
                for event in pygame.event.get():
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                            cap.release()
                            return False
                        elif event.key == pygame.K_SPACE:
                            # Forcer sync
                            self.content_manager.sync_contents()
            
            cap.release()
            return True
            
        except Exception as e:
            print(f"❌ Erreur affichage vidéo {filepath}: {e}")
            return False
    
    def update_media_contents(self):
        """Met à jour la liste des contenus média"""
        if time.time() - self.last_content_check > 30:  # Vérifier toutes les 30s
            self.media_contents = self.content_manager.get_available_contents()
            self.last_content_check = time.time()
            if self.media_contents:
                print(f"📋 {len(self.media_contents)} contenus média disponibles")
    
    def run(self):
        """Boucle principale d'affichage - contenus serveur uniquement"""
        print("🚀 Démarrage de l'affichage dynamique JUNIA - Mode serveur uniquement")
        
        # Test de connexion
        if not self.content_manager.test_server_connection():
            print("⚠️  Impossible de se connecter au serveur")
        
        # Synchronisation initiale
        self.content_manager.sync_contents()
        
        # Démarrer la synchronisation automatique
        self.content_manager.start_sync_thread()
        
        # Variables de timing
        page_start_time = pygame.time.get_ticks()
        current_content_index = 0
        
        running = True
        
        while running:
            current_time = pygame.time.get_ticks()
            
            # Gestion des événements
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        print("🔄 Synchronisation manuelle...")
                        self.content_manager.sync_contents()
                    elif event.key == pygame.K_RIGHT:
                        # Forcer passage au contenu suivant
                        page_start_time = 0
            
            # Mettre à jour les contenus média disponibles
            self.update_media_contents()
            
            # Si aucun contenu disponible, afficher écran d'attente
            if not self.media_contents:
                self.show_waiting_screen()
                time.sleep(1)
                continue
            
            # Calculer la durée d'affichage actuelle
            current_content = self.media_contents[current_content_index % len(self.media_contents)]
            content_duration = current_content['duration'] * 1000  # Convertir en ms
            
            # Vérifier si il faut changer de contenu
            if current_time - page_start_time >= content_duration:
                current_content_index = (current_content_index + 1) % len(self.media_contents)
                current_content = self.media_contents[current_content_index]
                
                print(f"📺 Affichage contenu: {current_content['name']} ({current_content['type']})")
                
                if current_content['type'] == 'image':
                    if self.display_image(current_content['filepath']):
                        pass  # Image affichée avec succès
                    else:
                        # Si erreur, passer au suivant
                        page_start_time = current_time
                        continue
                        
                elif current_content['type'] == 'video':
                    if not self.display_video(current_content['filepath'], current_content['duration']):
                        # Si erreur ou interruption, passer au suivant
                        page_start_time = current_time
                        continue
                
                page_start_time = current_time
            
            # Afficher le contenu actuel (pour les images)
            elif self.media_contents:
                current_content = self.media_contents[current_content_index % len(self.media_contents)]
                if current_content['type'] == 'image':
                    self.display_image(current_content['filepath'])
            
            self.clock.tick(60)  # 60 FPS
        
        # Nettoyage
        self.content_manager.stop()
        pygame.quit()
        print("👋 Affichage arrêté")

if __name__ == "__main__":
    try:
        affichage = AffichageBusWithServer()
        affichage.run()
    except KeyboardInterrupt:
        print("\n👋 Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        sys.exit(1)
