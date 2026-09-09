import requests
import os
import zipfile
from datetime import date
from utils_log import creer_logger

dossier_script = os.path.dirname(os.path.abspath(__file__))
logger = creer_logger("telecharger_population", dossier_script)

dossier_raw = os.path.join(dossier_script, "data", "raw", "population")
os.makedirs(dossier_raw, exist_ok=True)

# Créer l'arborescence RAW horodatée (par source / par année)
date_du_jour = date.today().isoformat()
dossier_raw = os.path.join(dossier_raw, date_du_jour)
os.makedirs(dossier_raw, exist_ok=True)

url = "https://www.data.gouv.fr/fr/datasets/r/ae305c99-d5a1-4854-b3bb-80b5cbe1f8e4"
chemin_zip = os.path.join(dossier_raw, "population_reference_2023.zip")

logger.info("Téléchargement de la population de référence...")
r = requests.get(url)
with open(chemin_zip, "wb") as f:
    f.write(r.content)

try:
    with zipfile.ZipFile(chemin_zip, "r") as z:
        z.extractall(dossier_raw)
    logger.info(f"  -> téléchargé et décompressé dans {dossier_raw}")
except NotImplementedError:
    logger.warning("  -> téléchargé MAIS décompression automatique impossible (à extraire manuellement avec 7-Zip)")
except zipfile.BadZipFile:
    logger.error("  -> le fichier n'est pas un ZIP valide (à vérifier manuellement)")

logger.info("Téléchargement population terminé.")
