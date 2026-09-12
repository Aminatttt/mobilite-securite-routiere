"""
29_val_coord_geo.py — Validation des coordonnees geographiques
================================================================
Controle la validite des coordonnees WGS84 produites par le script 28
(reprojeter_coordonnee.py) sur les vraies donnees CURATED du projet :
- plage de valeurs realiste (lat/lon dans les bornes theoriques de Paris)
- coordonnees manquantes ou hors plage
- pas de dependance a un fichier GeoJSON externe (jamais trace dans le
  catalogue de sourcing, donc non utilisable pour ce projet)
"""

import os
import pandas as pd

# Plage large de Paris et petite couronne (marge de securite, evite de rejeter
# a tort des accidents/troncons proches de la limite administrative)
LAT_MIN, LAT_MAX = 48.80, 48.92
LON_MIN, LON_MAX = 2.20, 2.50


def trouver_racine_projet(depart):
    dossier = depart
    while dossier != os.path.dirname(dossier):
        if os.path.exists(os.path.join(dossier, ".git")):
            return dossier
        dossier = os.path.dirname(dossier)
    raise FileNotFoundError("Racine du projet introuvable (pas de .git trouve)")


dossier_script = os.path.dirname(os.path.abspath(__file__))
racine_projet = trouver_racine_projet(dossier_script)
dossier_curated = os.path.join(racine_projet, "data", "curated")
dossier_docs = os.path.join(racine_projet, "docs")
os.makedirs(dossier_docs, exist_ok=True)

# Fichiers reels contenant des coordonnees, avec le nom de leurs colonnes lat/lon
# (alignes sur ce que produisent clean_baac.py et reprojeter_coordonnee.py corrige)
FICHIERS_A_VERIFIER = {
    "baac_caracteristiques": {
        "chemin": os.path.join(dossier_curated, "baac", "caracteristiques_paris_clean.csv"),
        "sep": ";",
        "col_lat": "lat",
        "col_lon": "long",
    },
    "referentiel_geo": {
        "chemin": os.path.join(dossier_curated, "referentiel_geo_paris_clean.csv"),
        "sep": ";",
        "col_lat": "lat_wgs84",
        "col_lon": "lon_wgs84",
    },
}


def valider_fichier(nom, config):
    chemin = config["chemin"]
    if not os.path.exists(chemin):
        print(f"[SKIP] {nom} : {chemin} introuvable.")
        return {
            "source": nom, "statut": "fichier introuvable",
            "lignes_totales": "N/A", "coord_manquantes": "N/A",
            "coord_hors_plage": "N/A", "coord_valides": "N/A",
        }

    df = pd.read_csv(chemin, sep=config["sep"], low_memory=False)
    col_lat, col_lon = config["col_lat"], config["col_lon"]

    if col_lat not in df.columns or col_lon not in df.columns:
        print(f"[ERREUR] {nom} : colonnes '{col_lat}'/'{col_lon}' absentes de {chemin}")
        print(f"          Colonnes disponibles : {list(df.columns)}")
        return {
            "source": nom, "statut": f"colonnes {col_lat}/{col_lon} absentes",
            "lignes_totales": len(df), "coord_manquantes": "N/A",
            "coord_hors_plage": "N/A", "coord_valides": "N/A",
        }

    lat = pd.to_numeric(df[col_lat], errors="coerce")
    lon = pd.to_numeric(df[col_lon], errors="coerce")

    lignes_totales = len(df)
    coord_manquantes = int((lat.isna() | lon.isna()).sum())

    dans_plage = (lat.between(LAT_MIN, LAT_MAX)) & (lon.between(LON_MIN, LON_MAX))
    coord_hors_plage = int((~dans_plage & lat.notna() & lon.notna()).sum())
    coord_valides = int((dans_plage).sum())

    print(f"[{nom}] {lignes_totales:,} lignes | "
          f"valides={coord_valides:,} | manquantes={coord_manquantes:,} | hors plage={coord_hors_plage:,}")

    if coord_hors_plage > 0:
        exemples = df.loc[~dans_plage & lat.notna() & lon.notna(), [col_lat, col_lon]].head(5)
        print(f"   Exemples hors plage :\n{exemples}")

    return {
        "source": nom, "statut": "OK",
        "lignes_totales": lignes_totales,
        "coord_manquantes": coord_manquantes,
        "coord_hors_plage": coord_hors_plage,
        "coord_valides": coord_valides,
    }


def main():
    print("=== Tache #29 : Validation des coordonnees geographiques ===\n")
    print(f"Plage de reference : lat [{LAT_MIN}, {LAT_MAX}] / lon [{LON_MIN}, {LON_MAX}]\n")

    resultats = []
    for nom, config in FICHIERS_A_VERIFIER.items():
        resultats.append(valider_fichier(nom, config))

    chemin_rapport = os.path.join(dossier_docs, "rapport_validation_coordonnees.csv")
    pd.DataFrame(resultats).to_csv(chemin_rapport, sep=";", index=False, encoding="utf-8-sig")
    print(f"\nRapport sauvegarde : {chemin_rapport}")
    print("=== Termine ===")


if __name__ == "__main__":
    main()