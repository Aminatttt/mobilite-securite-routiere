import requests
import os
import zipfile

dossier_script = os.path.dirname(os.path.abspath(__file__))
dossier_raw = os.path.join(dossier_script, "data", "raw", "trafic")
os.makedirs(dossier_raw, exist_ok=True)

annees = ["2020", "2021", "2022", "2023", "2024"]

for annee in annees:
    url = f"https://opendata.paris.fr/api/datasets/1.0/comptages-routiers-permanents-historique/attachments/opendata_txt_{annee}_zip/"
    chemin_zip = os.path.join(dossier_raw, f"trafic_{annee}.zip")

    print(f"Téléchargement du trafic {annee}...")
    r = requests.get(url)
    with open(chemin_zip, "wb") as f:
        f.write(r.content)

    dossier_extraction = os.path.join(dossier_raw, annee)
    os.makedirs(dossier_extraction, exist_ok=True)

    try:
        with zipfile.ZipFile(chemin_zip, "r") as z:
            z.extractall(dossier_extraction)
        print(f"  -> {annee} téléchargé et décompressé dans {dossier_extraction}")
    except NotImplementedError:
        print(f"  -> {annee} téléchargé Mais décompression automatique impossible (méthode de compression non supportée) — à extraire manuellement avec 7-Zip")
    except zipfile.BadZipFile:
        print(f"  -> {annee} : le fichier téléchargé n'est pas un ZIP valide (à vérifier manuellement)")

print("\nTéléchargement du trafic terminé pour toutes les années.")