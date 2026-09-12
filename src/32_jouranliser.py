"""
32_jouranliser.py — Journalisation des erreurs et anomalies ETL (Tache #32)
=============================================================================
CORRIGE : chemins alignes sur les vrais fichiers produits par clean_baac.py
(sous-dossier data/curated/baac/, separateur ';').
"""

from pathlib import Path
from datetime import datetime
import logging
import json

import pandas as pd


# ============================================================
# 1. CONFIGURATION DES CHEMINS
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CURATED_DIR = DATA_DIR / "curated"

LOG_DIR = SCRIPT_DIR / "logs"
LOG_FILE = LOG_DIR / "etl.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)
CURATED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. CONFIGURATION DU LOGGER
# ============================================================

logger = logging.getLogger("ETL")
logger.setLevel(logging.INFO)

if not logger.handlers:

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


# ============================================================
# 3. RAPPORT STRUCTURE DES ANOMALIES
# ============================================================

anomalies = []


def enregistrer_anomalie(categorie, niveau, fichier, description):
    anomalies.append({
        "date_detection": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "categorie": categorie,
        "niveau": niveau,
        "fichier": str(fichier),
        "description": description
    })

    message = f"[{categorie}] {fichier} - {description}"

    if niveau == "ERROR":
        logger.error(message)
    elif niveau == "WARNING":
        logger.warning(message)
    else:
        logger.info(message)


# ============================================================
# 4. VERIFICATION STRUCTURE DU PROJET
# ============================================================

def verifier_structure():
    logger.info("=" * 70)
    logger.info("VERIFICATION DE LA STRUCTURE DU PROJET")
    logger.info("=" * 70)

    dossiers_attendus = [
        RAW_DIR,
        CURATED_DIR,
        RAW_DIR / "baac",
        RAW_DIR / "meteo",
        RAW_DIR / "population",
        RAW_DIR / "referentiel_geo",
        RAW_DIR / "trafic",
    ]

    for dossier in dossiers_attendus:
        if dossier.exists():
            logger.info(f"Dossier present : {dossier}")
        else:
            enregistrer_anomalie(
                categorie="STRUCTURE", niveau="WARNING",
                fichier=dossier, description="Dossier attendu absent."
            )


# ============================================================
# 5. VERIFICATION DES FICHIERS BAAC
# ============================================================

def verifier_baac():
    logger.info("=" * 70)
    logger.info("VERIFICATION DES DONNEES BAAC")
    logger.info("=" * 70)

    baac_curated = CURATED_DIR / "baac"

    fichiers_attendus = {
        "caracteristiques": "caracteristiques_paris_clean.csv",
        "lieux": "lieux_paris_clean.csv",
        "usagers": "usagers_paris_clean.csv",
        "vehicules": "vehicules_paris_clean.csv",
    }

    if not baac_curated.exists():
        enregistrer_anomalie(
            categorie="STRUCTURE", niveau="ERROR",
            fichier=baac_curated, description="Dossier data/curated/baac absent."
        )
        return

    fichiers_present = list(baac_curated.glob("*.csv"))

    for nom_logique, nom_attendu in fichiers_attendus.items():
        fichier_attendu = baac_curated / nom_attendu

        if fichier_attendu.exists():
            logger.info(f"Fichier BAAC present : {nom_attendu}")
        else:
            variantes = []
            for fichier in fichiers_present:
                nom = fichier.name.lower()
                if nom_logique in nom:
                    variantes.append(fichier.name)
                elif nom_logique == "caracteristiques":
                    if "caract" in nom or "carcter" in nom or "caracter" in nom:
                        variantes.append(fichier.name)

            if variantes:
                enregistrer_anomalie(
                    categorie="NOM_FICHIER", niveau="WARNING",
                    fichier=fichier_attendu,
                    description=f"Fichier attendu absent : '{nom_attendu}'. Variante(s) detectee(s) : {', '.join(variantes)}."
                )
            else:
                enregistrer_anomalie(
                    categorie="FICHIER_MANQUANT", niveau="ERROR",
                    fichier=fichier_attendu, description="Fichier BAAC attendu introuvable."
                )


# ============================================================
# 6. VERIFICATION D'UN FICHIER BAAC
# ============================================================

def analyser_fichier_baac(fichier, colonnes_attendues):
    if not fichier.exists():
        return

    logger.info(f"Analyse du fichier : {fichier.name}")

    try:
        df = pd.read_csv(fichier, sep=";", low_memory=False)
    except Exception as e:
        enregistrer_anomalie(
            categorie="LECTURE", niveau="ERROR",
            fichier=fichier, description=f"Impossible de lire le fichier : {e}"
        )
        return

    if df.empty:
        enregistrer_anomalie(
            categorie="DONNEES", niveau="ERROR",
            fichier=fichier, description="Le fichier est vide."
        )
        return

    logger.info(f"{fichier.name} : {len(df)} lignes, {len(df.columns)} colonnes.")

    colonnes_absentes = set(colonnes_attendues) - set(df.columns)
    if colonnes_absentes:
        enregistrer_anomalie(
            categorie="COLONNE_MANQUANTE", niveau="ERROR",
            fichier=fichier,
            description="Colonnes attendues absentes : " + ", ".join(sorted(colonnes_absentes))
        )

    if "Num_Acc" in df.columns:
        nb_na = int(df["Num_Acc"].isna().sum())
        if nb_na > 0:
            enregistrer_anomalie(
                categorie="VALEURS_MANQUANTES", niveau="WARNING",
                fichier=fichier, description=f"{nb_na} valeur(s) manquante(s) dans Num_Acc."
            )

        nb_doublons = int(df["Num_Acc"].duplicated().sum())
        if nb_doublons > 0:
            enregistrer_anomalie(
                categorie="DOUBLONS", niveau="WARNING",
                fichier=fichier, description=f"{nb_doublons} doublon(s) detecte(s) sur Num_Acc."
            )

    for colonne in df.columns:
        nb_na = int(df[colonne].isna().sum())
        if nb_na > 0:
            pourcentage = (nb_na / len(df)) * 100
            if pourcentage >= 5:
                enregistrer_anomalie(
                    categorie="VALEURS_MANQUANTES", niveau="WARNING",
                    fichier=fichier,
                    description=f"Colonne '{colonne}' : {nb_na} valeur(s) manquante(s) ({pourcentage:.2f}%)."
                )


# ============================================================
# 7. ANALYSE COMPLETE DES FICHIERS BAAC
# ============================================================

def analyser_baac():
    fichiers = {
        "caracteristiques_paris_clean.csv": ["Num_Acc", "dep", "com", "an", "mois", "jour", "lat", "long"],
        "lieux_paris_clean.csv": ["Num_Acc"],
        "usagers_paris_clean.csv": ["Num_Acc"],
        "vehicules_paris_clean.csv": ["Num_Acc"],
    }

    for nom, colonnes in fichiers.items():
        fichier = CURATED_DIR / "baac" / nom
        analyser_fichier_baac(fichier, colonnes)


# ============================================================
# 8. VERIFICATION METEO
# ============================================================

def verifier_meteo():
    logger.info("=" * 70)
    logger.info("VERIFICATION DES DONNEES METEO")
    logger.info("=" * 70)

    meteo_dir = CURATED_DIR / "meteo"

    if not meteo_dir.exists():
        enregistrer_anomalie(
            categorie="CHEMIN", niveau="ERROR",
            fichier=meteo_dir, description="Dossier meteo absent."
        )
        return

    fichiers = [
        "meteo_rrtvent_paris_clean.csv",
        "meteo_autres_paris_clean.csv",
        "meteo_paris_reference_daily.csv",
    ]

    for nom in fichiers:
        fichier = meteo_dir / nom

        if not fichier.exists():
            enregistrer_anomalie(
                categorie="FICHIER_MANQUANT", niveau="WARNING",
                fichier=fichier, description="Fichier meteo attendu absent."
            )
            continue

        try:
            df = pd.read_csv(fichier, sep=";", low_memory=False)
            logger.info(f"{nom} : {len(df)} lignes, {len(df.columns)} colonnes.")

            if df.empty:
                enregistrer_anomalie(
                    categorie="DONNEES", niveau="ERROR",
                    fichier=fichier, description="Fichier meteo vide."
                )

            if "AAAAMMJJ" not in df.columns and "date" not in df.columns:
                enregistrer_anomalie(
                    categorie="CLE_JOINTURE", niveau="WARNING",
                    fichier=fichier, description="Colonne AAAAMMJJ / date absente."
                )

            if "NUM_POSTE" not in df.columns:
                enregistrer_anomalie(
                    categorie="CLE_JOINTURE", niveau="WARNING",
                    fichier=fichier, description="Colonne NUM_POSTE absente."
                )

        except Exception as e:
            enregistrer_anomalie(
                categorie="LECTURE", niveau="ERROR",
                fichier=fichier, description=f"Erreur lors de la lecture : {e}"
            )


# ============================================================
# 9. VERIFICATION DU REFERENTIEL GEO
# ============================================================

def verifier_referentiel_geo():
    logger.info("=" * 70)
    logger.info("VERIFICATION DU REFERENTIEL GEOGRAPHIQUE")
    logger.info("=" * 70)

    candidats = [
        RAW_DIR / "referentiel_geo",
    ]

    dossier_trouve = None

    for dossier in candidats:
        if dossier.exists():
            fichiers_json = list(dossier.rglob("*.json"))
            if fichiers_json:
                dossier_trouve = dossier
                logger.info(f"Referentiel geographique trouve dans : {dossier}")
                break

    if dossier_trouve is None:
        enregistrer_anomalie(
            categorie="FICHIER_MANQUANT", niveau="WARNING",
            fichier="referentiel_geo",
            description="Aucun fichier JSON du referentiel geographique trouve."
        )
        return

    fichiers_json = list(dossier_trouve.rglob("*.json"))

    for fichier in fichiers_json:
        try:
            with open(fichier, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                enregistrer_anomalie(
                    categorie="FORMAT", niveau="WARNING",
                    fichier=fichier, description="Le JSON ne contient pas une liste d'enregistrements."
                )
                continue

            logger.info(f"{fichier.name} : {len(data)} enregistrements.")

            if len(data) == 0:
                enregistrer_anomalie(
                    categorie="DONNEES", niveau="ERROR",
                    fichier=fichier, description="Le referentiel geographique est vide."
                )
                continue

            nb_sans_iu_ac = sum(1 for record in data if not record.get("iu_ac"))

            if nb_sans_iu_ac > 0:
                enregistrer_anomalie(
                    categorie="CLE_JOINTURE", niveau="WARNING",
                    fichier=fichier, description=f"{nb_sans_iu_ac} enregistrement(s) sans iu_ac."
                )

        except Exception as e:
            enregistrer_anomalie(
                categorie="LECTURE", niveau="ERROR",
                fichier=fichier, description=f"Erreur de lecture du JSON : {e}"
            )


# ============================================================
# 10. VERIFICATION TRAFIC
# ============================================================

def verifier_trafic():
    logger.info("=" * 70)
    logger.info("VERIFICATION DES DONNEES TRAFIC")
    logger.info("=" * 70)

    candidats = [RAW_DIR / "trafic"]

    dossier_trouve = None

    for dossier in candidats:
        if dossier.exists():
            fichiers = [f for f in dossier.rglob("*") if f.is_file()]
            if fichiers:
                dossier_trouve = dossier
                logger.info(f"Donnees trafic trouvees dans : {dossier}")
                logger.info(f"Nombre de fichiers trafic : {len(fichiers)}")
                break

    if dossier_trouve is None:
        enregistrer_anomalie(
            categorie="FICHIER_MANQUANT", niveau="WARNING",
            fichier="trafic", description="Aucune donnee trafic detectee dans les emplacements connus."
        )


# ============================================================
# 11. VERIFICATION DES DATES BAAC
# ============================================================

def verifier_dates_baac():
    logger.info("=" * 70)
    logger.info("VERIFICATION DES DATES BAAC")
    logger.info("=" * 70)

    fichier = CURATED_DIR / "baac" / "caracteristiques_paris_clean.csv"

    if not fichier.exists():
        return

    try:
        df = pd.read_csv(fichier, sep=";", low_memory=False)

        colonnes = ["an", "mois", "jour"]

        if not all(colonne in df.columns for colonne in colonnes):
            return

        an = pd.to_numeric(df["an"], errors="coerce")
        mois = pd.to_numeric(df["mois"], errors="coerce")
        jour = pd.to_numeric(df["jour"], errors="coerce")

        dates = pd.to_datetime({"year": an, "month": mois, "day": jour}, errors="coerce")

        nb_dates_invalides = int(dates.isna().sum())

        if nb_dates_invalides > 0:
            enregistrer_anomalie(
                categorie="DATE", niveau="WARNING",
                fichier=fichier, description=f"{nb_dates_invalides} date(s) BAAC invalide(s) ou impossible(s)."
            )
        else:
            logger.info("Toutes les dates BAAC sont valides.")

    except Exception as e:
        enregistrer_anomalie(
            categorie="DATE", niveau="ERROR",
            fichier=fichier, description=f"Erreur pendant le controle des dates : {e}"
        )


# ============================================================
# 12. GENERATION DU RAPPORT CSV
# ============================================================

def generer_rapport():
    rapport = CURATED_DIR / "rapport_anomalies_etl.csv"

    if anomalies:
        df_rapport = pd.DataFrame(anomalies)
    else:
        df_rapport = pd.DataFrame(columns=["date_detection", "categorie", "niveau", "fichier", "description"])

    df_rapport.to_csv(rapport, sep=";", index=False, encoding="utf-8-sig")

    logger.info("=" * 70)
    logger.info(f"Rapport des anomalies cree : {rapport}")
    logger.info(f"Nombre total d'anomalies : {len(anomalies)}")


# ============================================================
# 13. RESUME FINAL
# ============================================================

def afficher_resume():
    nb_error = sum(1 for a in anomalies if a["niveau"] == "ERROR")
    nb_warning = sum(1 for a in anomalies if a["niveau"] == "WARNING")

    logger.info("=" * 70)
    logger.info("RESUME DU CONTROLE ETL")
    logger.info("=" * 70)
    logger.info(f"ERREURS : {nb_error}")
    logger.info(f"AVERTISSEMENTS : {nb_warning}")

    if nb_error == 0 and nb_warning == 0:
        logger.info("Aucune anomalie detectee.")
    elif nb_error == 0:
        logger.info("Controle termine avec des avertissements.")
    else:
        logger.error("Controle termine avec des erreurs.")

    logger.info(f"Journal : {LOG_FILE}")


# ============================================================
# 14. PROGRAMME PRINCIPAL
# ============================================================

def main():
    logger.info("")
    logger.info("=" * 70)
    logger.info("DEMARRAGE DU CONTROLE ET DE LA JOURNALISATION ETL")
    logger.info("=" * 70)
    logger.info(f"Projet : {BASE_DIR}")

    try:
        verifier_structure()
        verifier_baac()
        analyser_baac()
        verifier_meteo()
        verifier_referentiel_geo()
        verifier_trafic()
        verifier_dates_baac()

    except Exception as e:
        enregistrer_anomalie(
            categorie="ETL", niveau="ERROR",
            fichier="journaliser_etl.py", description=f"Erreur generale inattendue : {e}"
        )

    finally:
        generer_rapport()
        afficher_resume()
        logger.info("=" * 70)
        logger.info("FIN DU CONTROLE ETL")
        logger.info("=" * 70)


if __name__ == "__main__":
    main()