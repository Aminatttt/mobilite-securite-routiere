import requests
import json
import os
from datetime import date
from utils_log import creer_logger

dossier_script = os.path.dirname(os.path.abspath(__file__))
logger = creer_logger("telecharger_referentiel_geo", dossier_script)

dossier_raw = os.path.join(dossier_script, "data", "raw", "referentiel_geo")
os.makedirs(dossier_raw, exist_ok=True)

# Créer l'arborescence RAW horodatée (par source / par année)
date_du_jour = date.today().isoformat()
dossier_raw = os.path.join(dossier_raw, date_du_jour)
os.makedirs(dossier_raw, exist_ok=True)

url_base = "https://parisdata.opendatasoft.com/api/explore/v2.1/catalog/datasets/referentiel-comptages-routiers/records"
taille_page = 100
offset = 0
tous_les_tronçons = []

while True:
    params = {"limit": taille_page, "offset": offset}
    r = requests.get(url_base, params=params)
    data = r.json()

    resultats = data.get("results", [])
    if not resultats:
        break

    tous_les_tronçons.extend(resultats)
    logger.info(f"Récupérés jusqu'ici : {len(tous_les_tronçons)}")

    offset += taille_page

logger.info(f"Total final : {len(tous_les_tronçons)} tronçons")

chemin_sortie = os.path.join(dossier_raw, "referentiel_geo.json")
with open(chemin_sortie, "w", encoding="utf-8") as f:
    json.dump(tous_les_tronçons, f, ensure_ascii=False, indent=2)

logger.info(f"Sauvegardé dans : {chemin_sortie}")
