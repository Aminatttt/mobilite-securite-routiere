"""
clean_referentiel_geo.py — ETL Référentiel Géographique Paris
=============================================================
Nettoyage et structuration du référentiel des voies et tronçons.
Source RAW : data/raw/referentiel_geo/
Sortie : data/curated/referentiel_geo_paris_clean.csv
"""
import json
from pathlib import Path
import pandas as pd
from utils_log import creer_logger

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
logger = creer_logger("clean_referentiel_geo", SCRIPT_DIR)

DOSSIER_RAW = BASE_DIR / "data" / "raw" / "referentiel_geo"
DOSSIER_CURATED = BASE_DIR / "data" / "curated"
DOSSIER_CURATED.mkdir(parents=True, exist_ok=True)

def main():
    logger.info("=== Debut nettoyage Referentiel Geographique ===")
    if not DOSSIER_RAW.exists():
        logger.error(f"Dossier introuvable : {DOSSIER_RAW}")
        return

    fichiers = list(DOSSIER_RAW.glob("**/*.json")) + list(DOSSIER_RAW.glob("**/*.csv"))
    if not fichiers:
        logger.error("Aucun fichier source trouve pour le referentiel geo.")
        return

    chemin = fichiers[0]
    logger.info(f"Lecture du fichier : {chemin.name}")
    
    if chemin.suffix.lower() == ".json":
        df = pd.read_json(chemin)
    else:
        df = pd.read_csv(chemin, sep=";", encoding="utf-8", low_memory=False)

    lignes_initiales = len(df)
    
    # Correction : Conversion des colonnes de type dict/list en str pour autoriser drop_duplicates
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, (dict, list))).any():
            df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x)

    df = df.dropna(how="all").drop_duplicates()

    # Normalisation des entetes de colonnes
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    chemin_sortie = DOSSIER_CURATED / "referentiel_geo_paris_clean.csv"
    df.to_csv(chemin_sortie, sep=";", index=False, encoding="utf-8-sig")
    
    logger.info(f"Nettoyage termine : {lignes_initiales} -> {len(df)} lignes")
    logger.info(f"Fichier de sortie : {chemin_sortie}")

if __name__ == "__main__":
    main()
    