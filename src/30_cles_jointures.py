"""
Tâche #30 — Construire les clés de jointure (Num_Acc, iu_ac, AAAAMMJJ, GEO)

Version "direct RAW" : au lieu d'attendre que chaque nettoyer_*.py ait tourné,
ce script lit directement data/raw/, applique le minimum de nettoyage commun
à l'équipe (filtre Paris dep=75 pour BAAC, correction virgule->point sur
lat/long), PUIS construit les 4 clés de jointure et sauvegarde dans
data/curated/.

Si vous avez déjà des fichiers dans data/curated/ produits par vos propres
nettoyer_*.py, ce script les utilise en priorité pour trafic / référentiel
géo / météo / population (il ne réinvente le nettoyage que pour BAAC, pour
lequel on lit le RAW directement).

Clés construites :
    - Num_Acc   : identifiant accident BAAC -> joint caract / lieux / usagers / vehicules
    - iu_ac     : identifiant arc de circulation -> joint trafic / référentiel géo
    - AAAAMMJJ  : date au format AAAAMMJJ (str) -> joint accidents / trafic / météo
    - GEO       : clé spatiale (lat/long arrondis à 4 décimales, ~11 m)
"""

import os
import pandas as pd

# ------------------------------------------------------------------
# Réglages
# ------------------------------------------------------------------
FILTRER_PARIS = True   # dep == '75', comme dans nettoyer_baac_ANAS.py
DECIMALES_GEO = 4      # précision de la clé GEO (~11 m à 4 décimales)


def trouver_racine_projet(depart):
    dossier = depart
    while dossier != os.path.dirname(dossier):
        if os.path.exists(os.path.join(dossier, ".git")):
            return dossier
        dossier = os.path.dirname(dossier)
    raise FileNotFoundError("Racine du projet introuvable (pas de .git trouvé)")


def trouver_dossier_plus_recent(chemin_source):
    sous_dossiers = [d for d in os.listdir(chemin_source) if os.path.isdir(os.path.join(chemin_source, d))]
    if not sous_dossiers:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {chemin_source}")
    sous_dossiers.sort(reverse=True)
    return os.path.join(chemin_source, sous_dossiers[0])


dossier_script = os.path.dirname(os.path.abspath(__file__))
racine_projet = trouver_racine_projet(dossier_script)
dossier_raw = os.path.join(racine_projet, "data", "raw")
dossier_curated = os.path.join(racine_projet, "data", "curated")


# ------------------------------------------------------------------
# 1. BAAC : lu directement depuis data/raw/baac/<dernier_run>/
# ------------------------------------------------------------------
def charger_baac():
    dossier_baac_brut = os.path.join(dossier_raw, "baac")
    if not os.path.isdir(dossier_baac_brut):
        print("[SKIP] data/raw/baac introuvable.")
        return {}

    dossier_dernier_run = trouver_dossier_plus_recent(dossier_baac_brut)
    print(f"[BAAC] dossier utilisé : {dossier_dernier_run}")

    fichiers = {
        "baac_caracteristiques": "Caract_2024.csv",
        "baac_lieux": "Lieux_2024.csv",
        "baac_usagers": "Usagers_2024.csv",
        "baac_vehicules": "Vehicules_2024.csv",
    }

    dfs = {}
    for nom, nom_fichier in fichiers.items():
        chemin = os.path.join(dossier_dernier_run, nom_fichier)
        if not os.path.exists(chemin):
            print(f"[SKIP] {nom} : {chemin} introuvable.")
            continue
        df = pd.read_csv(chemin, sep=";", encoding="latin-1", low_memory=False)
        print(f"[OK]   {nom} : {len(df)} lignes brutes.")
        dfs[nom] = df

    if "baac_caracteristiques" not in dfs:
        return dfs

    # Correction lat/long (virgule -> point) sur caracteristiques
    df_c = dfs["baac_caracteristiques"]
    if df_c["lat"].dtype == object:
        df_c["lat"] = df_c["lat"].str.replace(",", ".", regex=False).astype(float)
        df_c["long"] = df_c["long"].str.replace(",", ".", regex=False).astype(float)

    if FILTRER_PARIS and "dep" in df_c.columns:
        avant = len(df_c)
        df_c = df_c[df_c["dep"].astype(str).str.strip() == "75"].copy()
        print(f"[BAAC] filtre Paris (dep=75) : {avant} -> {len(df_c)} lignes")
    dfs["baac_caracteristiques"] = df_c

    # Filtrer les 3 autres fichiers sur les Num_Acc retenus (Paris ou tous)
    num_acc_retenus = set(df_c["Num_Acc"].unique())
    for nom in ["baac_lieux", "baac_usagers", "baac_vehicules"]:
        if nom in dfs:
            avant = len(dfs[nom])
            dfs[nom] = dfs[nom][dfs[nom]["Num_Acc"].isin(num_acc_retenus)].copy()
            print(f"[BAAC] {nom} filtré sur Num_Acc retenus : {avant} -> {len(dfs[nom])} lignes")

    return dfs


# ------------------------------------------------------------------
# 2. Autres sources : on tente le curated existant (si un nettoyer_*.py a
#    déjà tourné), sinon on skip proprement.
#
#    MIS A JOUR (post-refonte 24_1 / 26) :
#      - trafic       -> data/curated/trafic/trafic_2020_2024_agrege_semaine_clean.csv (sep ";")
#      - population   -> data/curated/population/population_paris_2023.csv (sep ";")
# ------------------------------------------------------------------
AUTRES_FICHIERS = {
    "trafic": (
        os.path.join(dossier_curated, "trafic", "trafic_2020_2024_agrege_semaine_clean.csv"),
        ";",
    ),
    "referentiel_geo": (
        os.path.join(dossier_curated, "referentiel_geo_nettoye.csv"),
        ",",
    ),
    "meteo": (
        os.path.join(dossier_curated, "meteo_nettoye.csv"),
        ",",
    ),
    "population": (
        os.path.join(dossier_curated, "population", "population_paris_2023.csv"),
        ";",
    ),
}


def charger_autres():
    dfs = {}
    for nom, (chemin, sep) in AUTRES_FICHIERS.items():
        if os.path.exists(chemin):
            df = pd.read_csv(chemin, sep=sep, low_memory=False)
            print(f"[OK]   {nom} : {len(df)} lignes ({chemin})")
            dfs[nom] = df
        else:
            print(f"[SKIP] {nom} : {chemin} introuvable (pas encore nettoyé).")
    return dfs


# ------------------------------------------------------------------
# 3. Construction des clés
# ------------------------------------------------------------------
CANDIDATS_LAT = ["lat", "latitude", "y_wgs84", "Y"]
CANDIDATS_LON = ["long", "lon", "longitude", "x_wgs84", "X"]

# "t_debut" ajouté : le nouveau fichier trafic agrégé par semaine (24_1) n'a
# plus de colonne "t_1h" horaire, mais une colonne "t_debut" (début de la
# semaine agrégée) qui sert de date de référence pour la clé AAAAMMJJ.
CANDIDATS_DATETIME = ["t_1h", "t_debut", "date", "datetime", "date_heure"]


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
    annee = df["an"].astype(int)
    annee = annee.apply(lambda a: a + 2000 if a < 100 else a)
    df["AAAAMMJJ"] = (
        annee.astype(str)
        + df["mois"].astype(int).astype(str).str.zfill(2)
        + df["jour"].astype(int).astype(str).str.zfill(2)
    )
    return df


def ajouter_cle_date_generique(df):
    if "AAAAMMJJ" in df.columns:
        df["AAAAMMJJ"] = df["AAAAMMJJ"].astype(str).str.strip()
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


def sauvegarder(nom, df, sous_dossier=None):
    dossier_sortie = os.path.join(dossier_curated, sous_dossier) if sous_dossier else dossier_curated
    os.makedirs(dossier_sortie, exist_ok=True)
    chemin = os.path.join(dossier_sortie, f"{nom}_cles.csv")
    df.to_csv(chemin, index=False)
    print(f"   -> sauvegardé : {chemin} ({len(df)} lignes, {df.shape[1]} colonnes)")


def main():
    print("=== Construction des clés de jointure (tâche #30, depuis RAW) ===\n")

    # --- BAAC ---
    dfs_baac = charger_baac()
    if "baac_caracteristiques" in dfs_baac:
        df = ajouter_cle_num_acc(dfs_baac["baac_caracteristiques"])
        df = ajouter_cle_date_baac(df)
        df = ajouter_cle_geo(df)
        sauvegarder("caracteristiques_paris_2024", df, sous_dossier="baac")

    for nom in ["baac_lieux", "baac_usagers", "baac_vehicules"]:
        if nom in dfs_baac:
            df = ajouter_cle_num_acc(dfs_baac[nom])
            suffixe = nom.replace("baac_", "")
            sauvegarder(f"{suffixe}_paris_2024", df, sous_dossier="baac")

    # --- Autres sources ---
    print()
    dfs_autres = charger_autres()

    if "trafic" in dfs_autres:
        df = ajouter_cle_iu_ac(dfs_autres["trafic"])
        df = ajouter_cle_date_generique(df)
        sauvegarder("trafic_nettoye", df)

    if "referentiel_geo" in dfs_autres:
        df = ajouter_cle_iu_ac(dfs_autres["referentiel_geo"])
        df = ajouter_cle_geo(df)
        sauvegarder("referentiel_geo_nettoye", df)

    if "meteo" in dfs_autres:
        df = ajouter_cle_date_generique(dfs_autres["meteo"])
        sauvegarder("meteo_nettoye", df)

    if "population" in dfs_autres:
        df = ajouter_cle_geo(dfs_autres["population"])
        sauvegarder("population_paris_nettoye", df)

    print("\n=== Terminé. ===")


if __name__ == "__main__":
    main()