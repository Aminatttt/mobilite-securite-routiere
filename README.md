import os
import pandas as pd

dossier_script = os.path.dirname(os.path.abspath(__file__))
dossier_projet = os.path.dirname(dossier_script)  # remonte d'un niveau (racine du projet)

dossier_sample = os.path.join(dossier_projet, "data", "sample")
os.makedirs(dossier_sample, exist_ok=True)

# Adapte ce chemin à ton dossier RAW horodaté le plus récent
# Exemple : data/raw/baac/2026-09-09/caract-2024.csv
fichiers_a_echantillonner = {
    "baac_caract_2024_sample.csv": "data/raw/baac/2026-09-09/Caract_2024.csv",
    "trafic_2024_sample.txt": None,  # à compléter avec le bon chemin .txt
    "meteo_sample.csv": "data/raw/meteo/2026-09-09/Q_75_previous-1950-2024_RR-T-Vent.csv",
}

for nom_sortie, chemin_relatif in fichiers_a_echantillonner.items():
    if chemin_relatif is None:
        continue
    chemin_complet = os.path.join(dossier_projet, chemin_relatif)
    if not os.path.exists(chemin_complet):
        print(f"Fichier introuvable, à vérifier : {chemin_complet}")
        continue

    df = pd.read_csv(chemin_complet, sep=";", nrows=50, encoding="latin-1")
    chemin_sortie = os.path.join(dossier_sample, nom_sortie)
    df.to_csv(chemin_sortie, sep=";", index=False)
    print(f"Échantillon créé : {chemin_sortie}")
