import requests
import os
from datetime import date

dossier_script = os.path.dirname(os.path.abspath(__file__))
dossier_raw = os.path.join(dossier_script, "data", "raw", "meteo")
os.makedirs(dossier_raw, exist_ok=True)

date_du_jour = date.today().isoformat()
dossier_raw = os.path.join(dossier_raw, date_du_jour)
os.makedirs(dossier_raw, exist_ok=True)

fichiers_meteo = {
    "Q_75_previous-1950-2024_RR-T-Vent.csv": "https://www.data.gouv.fr/fr/datasets/r/27bf7b0f-62a8-438f-acf4-b5f58d293322",
    "Q_75_previous-1950-2024_autres-parametres.csv": "https://www.data.gouv.fr/fr/datasets/r/e318ff1d-afab-494d-ab45-263bdc5cc2e2",
}

for nom_fichier, url in fichiers_meteo.items():
    chemin_destination = os.path.join(dossier_raw, nom_fichier)
    print(f"Téléchargement de {nom_fichier}...")
    r = requests.get(url)
    with open(chemin_destination, "wb") as f:
        f.write(r.content)
    print(f"  -> enregistré dans {chemin_destination}")

print("\nTéléchargement météo terminé.")