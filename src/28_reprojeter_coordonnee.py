"""
reprojeter_coordonnee.py — Extraction lat/lon WGS84 depuis le referentiel geographique
========================================================================================
CORRECTION : le referentiel geographique (confirme via l'API Opendatasoft en Phase 0)
est deja en WGS84, pas en Lambert 93. Il n'y a donc pas de reprojection a faire, mais
une simple EXTRACTION des coordonnees depuis le champ 'geo_point_2d' vers deux colonnes
separees lat_wgs84 / lon_wgs84, utilisables pour la carte et les jointures.

Le trafic n'a pas de coordonnees propres (seulement 'iu_ac') : la jointure geographique
se fera via iu_ac -> referentiel_geo en Phase 3, pas ici.
"""
import ast
import json
from pathlib import Path

import pandas as pd

from utils_log import creer_logger

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
logger = creer_logger("reprojeter_coordonnees", SCRIPT_DIR)

DOSSIER_CURATED = BASE_DIR / "data" / "curated"


def extraire_lat_lon(valeur):
    """Extrait (lat, lon) depuis geo_point_2d, quel que soit son format d'origine
    (dict Python, JSON, ou chaine 'lat,lon')."""
    if pd.isna(valeur):
        return None, None

    # Cas 1 : deja un dict (rare si lu depuis CSV, mais possible depuis JSON)
    if isinstance(valeur, dict):
        return valeur.get("lat"), valeur.get("lon")

    texte = str(valeur).strip()

    # Cas 2 : ressemble a un dict/JSON serialise en texte, ex: "{'lon': 2.37, 'lat': 48.85}"
    if texte.startswith("{"):
        try:
            d = json.loads(texte.replace("'", '"'))
        except (json.JSONDecodeError, ValueError):
            try:
                d = ast.literal_eval(texte)
            except (ValueError, SyntaxError):
                return None, None
        return d.get("lat"), d.get("lon")

    # Cas 3 : chaine simple "lat,lon" (format le plus courant venant d'un export CSV)
    if "," in texte:
        parties = texte.split(",")
        if len(parties) == 2:
            try:
                lat = float(parties[0].strip())
                lon = float(parties[1].strip())
                return lat, lon
            except ValueError:
                return None, None

    return None, None


def traiter_referentiel_geo():
    chemin_csv = DOSSIER_CURATED / "referentiel_geo_paris_clean.csv"

    if not chemin_csv.exists():
        logger.error(f"Fichier non trouve : {chemin_csv}")
        return

    logger.info(f"Traitement de {chemin_csv.name}...")
    df = pd.read_csv(chemin_csv, sep=";", low_memory=False)

    colonne_geo = next((c for c in df.columns if "geo_point" in c.lower()), None)
    if colonne_geo is None:
        logger.error(f"Aucune colonne de type 'geo_point_2d' trouvee dans {chemin_csv.name}")
        logger.error(f"Colonnes disponibles : {list(df.columns)}")
        return

    resultats = df[colonne_geo].apply(extraire_lat_lon)
    df["lat_wgs84"] = resultats.apply(lambda t: t[0])
    df["lon_wgs84"] = resultats.apply(lambda t: t[1])

    nb_valides = df["lat_wgs84"].notna().sum()
    logger.info(f"Coordonnees extraites : {nb_valides:,} / {len(df):,} lignes")

    if nb_valides == 0:
        logger.warning(
            f"Aucune coordonnee extraite depuis '{colonne_geo}' — verifier manuellement "
            f"un exemple de valeur : {df[colonne_geo].dropna().iloc[0] if df[colonne_geo].notna().any() else 'colonne vide'}"
        )

    df.to_csv(chemin_csv, sep=";", index=False, encoding="utf-8-sig")
    logger.info(f"Fichier mis a jour : {chemin_csv}")


logger.info("=== Debut Etape 28 : Extraction des coordonnees WGS84 ===")
traiter_referentiel_geo()
logger.info("=== Fin Etape 28 ===")
logger.info("NOTE : le trafic n'a pas de coordonnees propres — jointure via iu_ac en Phase 3")