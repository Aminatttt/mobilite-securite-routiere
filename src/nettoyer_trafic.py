import time
import pandas as pd
from pathlib import Path
from utils_log import creer_logger



SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent

RAW_TRAFIC_DIR = BASE_DIR / "data" / "raw" / "trafic"
CURATED_DIR = BASE_DIR / "data" / "curated"

CURATED_DIR.mkdir(parents=True, exist_ok=True)
logger = creer_logger("nettoyer_trafic_auto", str(SCRIPT_DIR))

def nettoyer_donnees():
    # Recherche de tous les fichiers de trafic (.csv, .txt, .xlsx) dans l'arborescence raw/trafic
    fichiers_trouves = (
        list(RAW_TRAFIC_DIR.glob("**/*.csv")) + 
        list(RAW_TRAFIC_DIR.glob("**/*.txt")) + 
        list(RAW_TRAFIC_DIR.glob("**/*.xlsx"))
    )
    
    if not fichiers_trouves:
        return

    # Sélection du fichier le plus récent
    chemin_fichier = max(fichiers_trouves, key=lambda p: p.stat().st_mtime)
    chemin_sortie = CURATED_DIR / "trafic_paris_nettoye.csv"
    
    # Si le fichier nettoyé existe déjà et est plus récent que le fichier brut, on ne fait rien
    if chemin_sortie.exists() and chemin_sortie.stat().st_mtime >= chemin_fichier.stat().st_mtime:
        return

    logger.info(f"Nouveau fichier détecté : {chemin_fichier.name}. Lancement du nettoyage...")
    
    try:
        # Lecture selon le format du fichier (séparateur ';' pour les txt/csv de trafic)
        suffixe = chemin_fichier.suffix.lower()
        if suffixe in ['.csv', '.txt']:
            df = pd.read_csv(chemin_fichier, sep=';', quotechar='"', low_memory=False)
        else:
            df = pd.read_excel(chemin_fichier)
        
        # Nettoyer les noms de colonnes (majuscules et suppression des espaces)
        df.columns = df.columns.str.strip().str.upper()
        logger.info(f"Colonnes présentes : {list(df.columns)}")
        
        # Vérification des colonnes propres aux données de trafic affichées dans votre capture
        colonnes_requises = ['L_AVAL', 'T_1H']
        if all(col in df.columns for col in colonnes_requises):
            # Suppression des lignes où les informations essentielles manquent
            df_nettoye = df.dropna(subset=['L_AVAL', 'T_1H']).copy()
            
            # Nettoyage optionnel des espaces superflus dans les textes (ex: noms de voies)
            if 'L_AVAL' in df_nettoye.columns:
                df_nettoye['L_AVAL'] = df_nettoye['L_AVAL'].astype(str).str.strip()

            # Enregistrement du fichier propre au format CSV standard dans le dossier curated
            df_nettoye.to_csv(chemin_sortie, index=False, sep=',')
            logger.info(f"Nettoyage réussi ! Enregistré dans : {chemin_sortie}")
            print(f"[{time.strftime('%H:%M:%S')}] Succès : Données de trafic de Paris nettoyées et enregistrées !")
        else:
            logger.error(f"Structure non reconnue. Les colonnes {colonnes_requises} sont introuvables.")
            print(f"[{time.strftime('%H:%M:%S')}] Erreur : Colonnes de trafic requises absentes.")
            
    except Exception as e:
        logger.error(f"Erreur lors du traitement : {e}")

if __name__ == "__main__":
    print("Mode automatique activé : Surveillance intelligente du dossier trafic...")
    logger.info("Démarrage du script de surveillance automatique du trafic.")
    
    try:
        while True:
            nettoyer_donnees()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nArrêt du script automatique.")
