#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de vérification de l'installation Player
Vérifie que tous les fichiers et dépendances sont présents
"""

import os
import sys

def check_files():
    """Vérifie la présence de tous les fichiers nécessaires"""
    print("🔍 Vérification des fichiers...")
    
    required_files = {
        "affichageDynamique.py": "Script principal",
        "README.md": "Documentation",
        "requirements.txt": "Dépendances Python"
    }
    
    required_icons = [
        "sunny.png", "cloudy.png", "rainy.png", "windy.png",
        "junia.png", "ilevia.png", "temp.png", "humidity.png", "vlille.png",
        "busL5aller.png", "busL5retour.png", "bus18aller.png", "bus18retour.png"
    ]
    
    all_ok = True
    
    # Vérifier fichiers principaux
    for filename, description in required_files.items():
        if os.path.exists(filename):
            print(f"✅ {filename} ({description})")
        else:
            print(f"❌ {filename} MANQUANT ({description})")
            all_ok = False
    
    # Vérifier dossier icons
    if os.path.exists("icons"):
        print(f"✅ Dossier icons/")
        
        # Vérifier chaque icône
        for icon in required_icons:
            icon_path = os.path.join("icons", icon)
            if os.path.exists(icon_path):
                print(f"   ✅ {icon}")
            else:
                print(f"   ❌ {icon} MANQUANT")
                all_ok = False
    else:
        print(f"❌ Dossier icons/ MANQUANT")
        all_ok = False
    
    return all_ok

def check_dependencies():
    """Vérifie que les dépendances Python sont installées"""
    print("\n🔍 Vérification des dépendances Python...")
    
    dependencies = {
        "pygame": "Affichage graphique",
        "cv2": "Lecture vidéo (opencv-python)",
        "requests": "Requêtes HTTP"
    }
    
    all_ok = True
    
    for module, description in dependencies.items():
        try:
            __import__(module)
            print(f"✅ {module} ({description})")
        except ImportError:
            print(f"❌ {module} MANQUANT ({description})")
            print(f"   → Installer avec: pip install {module if module != 'cv2' else 'opencv-python'}")
            all_ok = False
    
    return all_ok

def check_script_syntax():
    """Vérifie la syntaxe du script principal"""
    print("\n🔍 Vérification de la syntaxe du script...")
    
    try:
        with open("affichageDynamique.py", "r", encoding="utf-8") as f:
            code = f.read()
            compile(code, "affichageDynamique.py", "exec")
        print("✅ Syntaxe Python valide")
        return True
    except SyntaxError as e:
        print(f"❌ Erreur de syntaxe : {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur de lecture : {e}")
        return False

def main():
    """Fonction principale"""
    print("=" * 60)
    print("📦 VÉRIFICATION INSTALLATION PLAYER AFFICHAGE DYNAMIQUE")
    print("=" * 60)
    print()
    
    # Vérifier que nous sommes dans le bon dossier
    if not os.path.exists("affichageDynamique.py"):
        print("❌ ERREUR : Exécuter ce script depuis le dossier Player/")
        print("   cd Player")
        print("   python check_installation.py")
        return False
    
    files_ok = check_files()
    deps_ok = check_dependencies()
    syntax_ok = check_script_syntax()
    
    print("\n" + "=" * 60)
    
    if files_ok and deps_ok and syntax_ok:
        print("✅ INSTALLATION COMPLÈTE ET FONCTIONNELLE")
        print()
        print("🚀 Pour lancer l'application :")
        print("   python affichageDynamique.py")
        print()
        print("📖 Consultez README.md pour la configuration")
        return True
    else:
        print("❌ INSTALLATION INCOMPLÈTE")
        print()
        if not files_ok:
            print("⚠️  Fichiers manquants - Vérifier la structure du dossier")
        if not deps_ok:
            print("⚠️  Dépendances manquantes - Installer avec:")
            print("   pip install -r requirements.txt")
        if not syntax_ok:
            print("⚠️  Erreur de syntaxe dans le script")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Vérification interrompue")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
