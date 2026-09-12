"""
Tâche #30 — Construire les clés de jointure (Num_Acc, iu_ac, AAAAMMJJ, GEO)

CORRIGÉ : pointe vers les vrais fichiers CURATED produits par les scripts
officiels de l'équipe (clean_baac.py, nettoyer_trafic.py corrigé,
clean_referentiel_geo.py, script météo complet, nettoyer_population.py),
et couvre les 5 années BAAC (pas seulement 2024).
"""

import os
import pandas as pd

DECIMALES_GEO = 4


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

# Chemins REELS des fichiers produits par les scripts officiels (verifies contre
# clean_baac.py, nettoyer_trafic.py, clean_referentiel_geo.py, script meteo complet,
# nettoyer_population.py). A adapter si un membre change un nom de sortie.
SOURCES = {
    "baac_caracteristiques": os.path.join(dossier_curated, "baac", "caracteristiques_paris_clean.csv"),
    "baac_lieux": os.path.join(dossier_curated, "baac", "lieux_paris_clean.csv"),
    "baac_usagers": os.path.join(dossier_curated, "baac", "usagers_paris_clean.csv"),
    "baac_vehicules": os.path.join(dossier_curated, "baac", "vehicules_paris_clean.csv"),
    "trafic": os.path.join(dossier_curated, "trafic", "trafic_2020_2024_agrege_semaine_clean.csv"),
    "referentiel_geo": os.path.join(dossier_curated, "referentiel_geo_paris_clean.csv"),
    "meteo": os.path.join(dossier_curated, "meteo", "meteo_paris_reference_daily.csv"),
    "population": os.path.join(dossier_curated, "population", "population_paris_2023.csv"),
}

SEPARATEURS = {
    "baac_caracteristiques": ";", "baac_lieux": ";", "baac_usagers": ";", "baac_vehicules": ";",
    "trafic": ";", "referentiel_geo": ";", "meteo": ";", "population": ";",
}

CANDIDATS_LAT = ["lat", "latitude", "lat_wgs84", "LAT"]
CANDIDATS_LON = ["long", "lon", "longitude", "lon_wgs84", "LON"]
CANDIDATS_DATETIME = ["t_debut", "date", "datetime", "date_heure"]


def charger(nom):
    chemin = SOURCES[nom]
    if not os.path.exists(chemin):
        print(f"[SKIP] {nom} : {chemin} introuvable.")
        return None
    df = pd.read_csv(chemin, sep=SEPARATEURS[nom], low_memory=False)
    print(f"[OK]   {nom} : {len(df):,} lignes ({chemin})")
    return df


def premiere_colonne_existante(df, candidats):
    for c in candidats:
        if c in df.columns:
            return c
    return None


def ajouter_cle_num_acc(df):
    if "Num_Acc" in df.columns:
        df["Num_Acc"] = df["Num_Acc"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    return df


def ajouter_cle_iu_ac(df):
    if "iu_ac" in df.columns:
        df["iu_ac"] = df["iu_ac"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    return df


def ajouter_cle_date_baac(df):
    if not all(c in df.columns for c in ["jour", "mois", "an"]):
        return df
    annee = pd.to_numeric(df["an"], errors="coerce")
    annee = annee.apply(lambda a: a + 2000 if pd.notna(a) and a < 100 else a)
    df["AAAAMMJJ"] = (
        annee.astype("Int64").astype(str)
        + pd.to_numeric(df["mois"], errors="coerce").astype("Int64").astype(str).str.zfill(2)
        + pd.to_numeric(df["jour"], errors="coerce").astype("Int64").astype(str).str.zfill(2)
    )
    return df


def ajouter_cle_date_generique(df):
    if "AAAAMMJJ" in df.columns:
        df["AAAAMMJJ"] = df["AAAAMMJJ"].astype(str).str.strip()
        return df
    if "date" in df.columns:
        dt = pd.to_datetime(df["date"], errors="coerce")
        df["AAAAMMJJ"] = dt.dt.strftime("%Y%m%d")
        return df
    col_dt = premiere_colonne_existante(df, CANDIDATS_DATETIME)
    if col_dt:
        dt = pd.to_datetime(df[col_dt], errors="coerce", utc=True)
        df["AAAAMMJJ"] = dt.dt.strftime("%Y%m%d")
    return df


def ajouter_cle_geo(df):
    col_lat = premiere_colonne_existante(df, CANDIDATS_LAT)
    col_lon = premiere_colonne_existante(df, CANDIDATS_LON)
    if not (col_lat and col_lon):
        return df
    lat = pd.to_numeric(df[col_lat], errors="coerce").round(DECIMALES_GEO)
    lon = pd.to_numeric(df[col_lon], errors="coerce").round(DECIMALES_GEO)
    df["GEO"] = lat.astype(str) + "_" + lon.astype(str)
    df.loc[lat.isna() | lon.isna(), "GEO"] = None
    return df


def sauvegarder(nom, df):
    dossier_sortie = os.path.join(dossier_curated, "cles_jointure")
    os.makedirs(dossier_sortie, exist_ok=True)
    chemin = os.path.join(dossier_sortie, f"{nom}_cles.csv")
    df.to_csv(chemin, index=False, sep=";")
    print(f"   -> sauvegarde : {chemin} ({len(df):,} lignes, {df.shape[1]} colonnes)")


def main():
    print("=== Construction des cles de jointure (tache #30) ===\n")

    df = charger("baac_caracteristiques")
    if df is not None:
        df = ajouter_cle_num_acc(df)
        df = ajouter_cle_date_baac(df)
        df = ajouter_cle_geo(df)
        sauvegarder("baac_caracteristiques", df)

    for nom in ["baac_lieux", "baac_usagers", "baac_vehicules"]:
        df = charger(nom)
        if df is not None:
            df = ajouter_cle_num_acc(df)
            sauvegarder(nom, df)

    df = charger("trafic")
    if df is not None:
        df = ajouter_cle_iu_ac(df)
        df = ajouter_cle_date_generique(df)
        sauvegarder("trafic", df)

    df = charger("referentiel_geo")
    if df is not None:
        df = ajouter_cle_iu_ac(df)
        df = ajouter_cle_geo(df)
        sauvegarder("referentiel_geo", df)

    df = charger("meteo")
    if df is not None:
        df = ajouter_cle_date_generique(df)
        sauvegarder("meteo", df)

    df = charger("population")
    if df is not None:
        df = ajouter_cle_geo(df)
        sauvegarder("population", df)

    print("\n=== Termine. ===")


if __name__ == "__main__":
    main()