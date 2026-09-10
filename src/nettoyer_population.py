import time
import pandas as pd
from pathlib import Path
from utils_log import creer_logger

# ==========================================
# CONFIGURATION
# ==========================================
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent

RAW_POP_DIR = BASE_DIR / "data" / "raw" / "population"
CURATED_DIR = BASE_DIR / "data" / "curated"

CURATED_DIR.mkdir(parents=True, exist_ok=True)
logger = creer_logger("nettoyer_population_auto", str(SCRIPT_DIR))

def nettoyer_donnees():
    fichiers_trouves = list(RAW_POP_DIR.glob("**/*.csv")) + list(RAW_POP_DIR.glob("**/*.xlsx"))
    
    if not fichiers_trouves:
        return

    chemin_fichier = max(fichiers_trouves, key=lambda p: p.stat().st_mtime)
    chemin_sortie = CURATED_DIR / "population_paris_nettoye.csv"
    
    if chemin_sortie.exists() and chemin_sortie.stat().st_mtime >= chemin_fichier.stat().st_mtime:
        return

    logger.info(f"Nouveau fichier détecté : {chemin_fichier.name}. Lancement du nettoyage...")
    
    try:
        if chemin_fichier.suffix.lower() == '.csv':
            df = pd.read_csv(chemin_fichier, sep=';', quotechar='"', low_memory=False)
        else:
            df = pd.read_excel(chemin_fichier)
        
        # Nettoyer les noms de colonnes
        df.columns = df.columns.str.strip().str.upper()
        logger.info(f"Colonnes présentes : {list(df.columns)}")
        
        # Adaptation au format INSEE (recherche de GEO ou d'une colonne de code)
        df_paris = None
        
        # Cas 1 : Format long avec COD_VAR / COD_MOD
        if 'COD_VAR' in df.columns and 'COD_MOD' in df.columns:
            mask_geo = (df['COD_VAR'].astype(str).str.upper() == 'GEO')
            mask_paris = df['COD_MOD'].astype(str).str.startswith('75')
            df_paris = df[mask_geo & mask_paris]
            
        else:
            # Cas 2 : Recherche dynamique d'une colonne de code département / commune
            col_cible = None
            for col in df.columns:
                if any(m in col.lower() for m in ['dep', 'geo', 'code', 'commune']):
                    col_cible = col
                    break
            if col_cible:
                df_paris = df[df[col_cible].astype(str).str.contains('75', na=False)]

        if df_paris is not None and not df_paris.empty:
            df_paris.to_csv(chemin_sortie, index=False, sep=',')
            logger.info(f"Nettoyage réussi ! Enregistré dans : {chemin_sortie}")
            print(f"[{time.strftime('%H:%M:%S')}] Succès : Données de population de Paris nettoyées et enregistrées !")
        else:
            logger.error("Aucune ligne correspondant à Paris (75) n'a pu être isolée.")
            print(f"[{time.strftime('%H:%M:%S')}] Erreur : Filtrage Paris introuvable.")
            
    except Exception as e:
        logger.error(f"Erreur lors du traitement : {e}")

if __name__ == "__main__":
    print("Mode automatique activé : Surveillance intelligente du dossier population...")
    logger.info("Démarrage du script de surveillance automatique.")
    
    try:
        while True:
            nettoyer_donnees()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nArrêt du script automatique.")
