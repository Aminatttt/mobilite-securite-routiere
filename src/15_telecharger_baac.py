import requests
import os
from datetime import date
from utils_log import creer_logger

def trouver_racine_projet(depart):
    dossier = depart
    while dossier != os.path.dirname(dossier):
        if os.path.exists(os.path.join(dossier, ".git")):
            return dossier
        dossier = os.path.dirname(dossier)
    raise FileNotFoundError("Racine du projet introuvable")

# --- Initialisation (logger + dossiers) ---
dossier_script = os.path.dirname(os.path.abspath(__file__))
logger = creer_logger("telecharger_baac", dossier_script)

racine_projet = trouver_racine_projet(dossier_script)
dossier_raw = os.path.join(racine_projet, "data", "raw", "baac")
os.makedirs(dossier_raw, exist_ok=True)

date_du_jour = date.today().isoformat()
dossier_raw = os.path.join(dossier_raw, date_du_jour)
os.makedirs(dossier_raw, exist_ok=True)

# --- Étape 1 : récupérer la liste des fichiers depuis l'API ---
DATASET_ID = "53698f4ca3a729239d2036df"
url_api = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_ID}/"

reponse = requests.get(url_api)
data = reponse.json()
fichiers = data["resources"]
logger.info(f"Nombre total de fichiers trouvés : {len(fichiers)}")

# --- Étape 2 : filtrer les fichiers BAAC 2020-2024 ---
annees_voulues = ["2020", "2021", "2022", "2023", "2024"]
types_voulus = ["caract", "carcteristiques", "lieux", "usagers", "vehicules"]

fichiers_baac = []
for f in fichiers:
    titre = f["title"].lower()
    for annee in annees_voulues:
        for type_fichier in types_voulus:
            if type_fichier in titre and annee in titre:
                fichiers_baac.append(f)

vus = set()
fichiers_baac_uniques = []
for f in fichiers_baac:
    if f["title"] not in vus:
        fichiers_baac_uniques.append(f)
        vus.add(f["title"])
fichiers_baac = fichiers_baac_uniques

logger.info(f"Fichiers BAAC 2020-2024 retenus après dédoublonnage : {len(fichiers_baac)}")
for f in fichiers_baac:
    logger.info(f"- {f['title']}")

# --- Étape 3 : télécharger chaque fichier ---
for f in fichiers_baac:
    nom_fichier = f["title"]
    lien = f["url"]
    chemin_destination = os.path.join(dossier_raw, nom_fichier)

    logger.info(f"Téléchargement de {nom_fichier}...")
    r = requests.get(lien)
    with open(chemin_destination, "wb") as fichier_local:
        fichier_local.write(r.content)

logger.info(f"Tous les fichiers BAAC ont été téléchargés dans : {dossier_raw}")