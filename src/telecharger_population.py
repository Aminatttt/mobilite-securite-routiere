import requests
import os
import zipfile
from datetime import date

dossier_script = os.path.dirname(os.path.abspath(__file__))
dossier_raw = os.path.join(dossier_script, "data", "raw", "population")
os.makedirs(dossier_raw, exist_ok=True)

date_du_jour = date.today().isoformat()
dossier_raw = os.path.join(dossier_raw, date_du_jour)
os.makedirs(dossier_raw, exist_ok=True)

url = "https://www.data.gouv.fr/fr/datasets/r/ae305c99-d5a1-4854-b3bb-80b5cbe1f8e4"
chemin_zip = os.path.join(dossier_raw, "population_reference_2023.zip")

print("Téléchargement de la population de référence...")
r = requests.get(url)
with open(chemin_zip, "wb") as f:
    f.write(r.content)

try:
    with zipfile.ZipFile(chemin_zip, "r") as z:
        z.extractall(dossier_raw)
    print("  -> téléchargé et décompressé dans", dossier_raw)
except NotImplementedError:
    print("  -> téléchargé MAIS décompression automatique impossible (à extraire manuellement avec 7-Zip)")
except zipfile.BadZipFile:
    print("  -> le fichier n'est pas un ZIP valide (à vérifier manuellement)")

print("\nTéléchargement population terminé.")