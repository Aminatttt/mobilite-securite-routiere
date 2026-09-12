import requests
import os
import zipfile
from datetime import date
from utils_log import creer_logger

def trouver_racine_projet(depart):
    dossier = depart
    while dossier != os.path.dirname(dossier):
        if os.path.exists(os.path.join(dossier, ".git")):
            return dossier
        dossier = os.path.dirname(dossier)
    raise FileNotFoundError("Racine du projet introuvable")

dossier_script = os.path.dirname(os.path.abspath(__file__))
logger = creer_logger("telecharger_trafic", dossier_script)

racine_projet = trouver_racine_projet(dossier_script)
dossier_raw = os.path.join(racine_projet, "data", "raw", "trafic")
os.makedirs(dossier_raw, exist_ok=True)

# Créer l'arborescence RAW horodatée (par source / par année)
date_du_jour = date.today().isoformat()
dossier_raw = os.path.join(dossier_raw, date_du_jour)
os.makedirs(dossier_raw, exist_ok=True)

annees = ["2020", "2021", "2022", "2023", "2024"]

for annee in annees:
    url = f"https://opendata.paris.fr/api/datasets/1.0/comptages-routiers-permanents-historique/attachments/opendata_txt_{annee}_zip/"
    chemin_zip = os.path.join(dossier_raw, f"trafic_{annee}.zip")

    logger.info(f"Téléchargement du trafic {annee}...")
    r = requests.get(url)
    with open(chemin_zip, "wb") as f:
        f.write(r.content)

    dossier_extraction = os.path.join(dossier_raw, annee)
    os.makedirs(dossier_extraction, exist_ok=True)

    try:
        with zipfile.ZipFile(chemin_zip, "r") as z:
            z.extractall(dossier_extraction)
        logger.info(f"  -> {annee} téléchargé et décompressé dans {dossier_extraction}")
    except NotImplementedError:
        logger.warning(f"  -> {annee} téléchargé MAIS décompression automatique impossible (méthode de compression non supportée) — à extraire manuellement avec 7-Zip")
    except zipfile.BadZipFile:
        logger.error(f"  -> {annee} : le fichier téléchargé n'est pas un ZIP valide (à vérifier manuellement)")

logger.info("Téléchargement du trafic terminé pour toutes les années.")