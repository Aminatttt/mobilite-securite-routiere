# Etape 1
import requests

DATASET_ID = "53698f4ca3a729239d2036df"
url_api = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_ID}/"

reponse = requests.get(url_api)
data = reponse.json()

fichiers = data["resources"]
print(f"Nombre total de fichiers trouvés : {len(fichiers)}")

# Etape 2 
annees_voulues = ["2020", "2021", "2022", "2023", "2024"]
types_voulus = ["caract", "carcteristiques", "lieux", "usagers", "vehicules"]
fichiers_baac = []

for f in fichiers:
    titre = f["title"].lower()
    for annee in annees_voulues:
        for type_fichier in types_voulus:
            if type_fichier in titre and annee in titre:
                fichiers_baac.append(f)

print(f"Fichiers BAAC 2020-2024 retenus : {len(fichiers_baac)}")
for f in fichiers_baac:
    print("-", f["title"])
    
vus = set()
fichiers_baac_uniques = []
for f in fichiers_baac:
    if f["title"] not in vus:
        fichiers_baac_uniques.append(f)
        vus.add(f["title"])

fichiers_baac = fichiers_baac_uniques
print(f"Après dédoublonnage : {len(fichiers_baac)} fichiers")

# etape 3
import os

dossier_script = os.path.dirname(os.path.abspath(__file__))
dossier_raw = os.path.join(dossier_script, "data", "raw", "baac")
os.makedirs(dossier_raw, exist_ok=True)

for f in fichiers_baac:
    nom_fichier = f["title"]
    lien = f["url"]
    chemin_destination = os.path.join(dossier_raw, nom_fichier)

    print(f"Téléchargement de {nom_fichier}...")
    r = requests.get(lien)
    with open(chemin_destination, "wb") as fichier_local:
        fichier_local.write(r.content)

print("\nTous les fichiers BAAC ont été téléchargés dans :", dossier_raw)