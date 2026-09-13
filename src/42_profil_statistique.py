from pathlib import Path
import pandas as pd


#  DÉFINITION DES CHEMINS 

DOSSIER_SCRIPT = Path(__file__).resolve().parent

RACINE_PROJET = (
    DOSSIER_SCRIPT.parent if DOSSIER_SCRIPT.name == "src" else DOSSIER_SCRIPT
)

DOSSIER_CURATED = RACINE_PROJET / "data" / "curated"
DOSSIER_PROFILS = DOSSIER_CURATED / "profils"
DOSSIER_PROFILS.mkdir(parents=True, exist_ok=True)

#  LECTURE ADAPTATIVE D'UN CSV 

def lire_csv_adaptatif(*chemins_relatifs: str) -> pd.DataFrame:
    for chemin_relatif in chemins_relatifs:

        chemin = DOSSIER_CURATED / chemin_relatif

        if not chemin.exists():
            continue

        for enc in ["utf-8-sig", "utf-8", "latin1"]:
            try:
                with open(chemin, "r", encoding=enc) as f:
                    premiere_ligne = f.readline()
                    separateur = ";" if ";" in premiere_ligne else ","
                print(f"  → lu : {chemin.relative_to(DOSSIER_CURATED)}")
                return pd.read_csv(chemin, sep=separateur, encoding=enc, low_memory=False)
            except UnicodeDecodeError:
                continue

    print(f"[ATTENTION] Aucun fichier trouvé parmi : {list(chemins_relatifs)}")
    return pd.DataFrame()


#  CONFIGURATION DES DATASETS À PROFILER 

DATASETS = {

    "caracteristiques": [
        "baac/caracteristiques_paris_2024_cles.csv",
        "baac/caracteristiques_paris_clean.csv",
    ],
    "usagers": [
        "baac/usagers_paris_2024_cles.csv",
        "baac/usagers_paris_clean.csv",
    ],
    "vehicules": [
        "baac/vehicules_paris_2024_cles.csv",
        "baac/vehicules_paris_clean.csv",
    ],
    "lieux": [
        "baac/lieux_paris_2024_cles.csv",
        "baac/lieux_paris_clean.csv",
    ],
    "meteo": [
        "meteo_nettoye_cles.csv",
        "meteo/meteo_paris_reference_daily.csv",
    ],
    "population": [
        "population_paris_nettoye_cles.csv",
        "population/population_paris_2023.csv",
    ],
    "referentiel_geo": [
        "referentiel_geo_nettoye_cles.csv",
        "referentiel_geo_paris_clean.csv",
    ],
    "trafic": [
        "trafic_nettoye_cles.csv",
        "trafic/trafic_2020_2024_agrege_semaine_clean.csv",
    ],
}

#  CALCUL DU PROFIL STATISTIQUE D'UN DATAFRAME

def profiler_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    nb_lignes = len(df)
    lignes_profil = []

    for colonne in df.columns:
        serie = df[colonne]
        nb_manquants = serie.isna().sum()
        nb_valeurs = nb_lignes - nb_manquants
        pct_manquants = round(100 * nb_manquants / nb_lignes, 2) if nb_lignes else 0
        nb_uniques = serie.nunique(dropna=True)
        est_numerique = pd.api.types.is_numeric_dtype(serie)

        profil = {
            "colonne": colonne,
            "type": str(serie.dtype),
            "nb_valeurs": nb_valeurs,
            "nb_manquants": nb_manquants,
            "pct_manquants": pct_manquants,
            "nb_uniques": nb_uniques,
            "min": None,
            "max": None,
            "moyenne": None,
            "mediane": None,
            "ecart_type": None,
            "top_3_valeurs": None,
        }
        if est_numerique and nb_valeurs > 0:
            serie_num = pd.to_numeric(serie, errors="coerce")
            profil["min"] = serie_num.min()
            profil["max"] = serie_num.max()
            profil["moyenne"] = round(serie_num.mean(), 3)
            profil["mediane"] = serie_num.median()
            profil["ecart_type"] = round(serie_num.std(), 3)

        elif nb_valeurs > 0:
            top = serie.value_counts(dropna=True).head(3)
            profil["top_3_valeurs"] = "; ".join(f"{val} ({eff})" for val, eff in top.items())

        lignes_profil.append(profil)
    return pd.DataFrame(lignes_profil)

#  TÂCHE 42 : profil statistique

def realiser_profil_statistique():
    print("=" * 80)
    print("TÂCHE 42 — PROFIL STATISTIQUE DES VARIABLES")
    print("=" * 80)

    if not DOSSIER_CURATED.exists():
        raise FileNotFoundError(f" Le dossier CURATED est introuvable : {DOSSIER_CURATED}")

    print(f"\n Dossier CURATED : {DOSSIER_CURATED}")
    print(f" Profils sauvegardés dans : {DOSSIER_PROFILS}")

    resume_global = []

    for nom_dataset, chemins in DATASETS.items():

        print("\n" + "-" * 80)
        print(f"DATASET : {nom_dataset}")
        print("-" * 80)

        df = lire_csv_adaptatif(*chemins)

        if df.empty:
            print(f"   {nom_dataset} : aucun fichier trouvé ou fichier vide, profil ignoré.")
            continue

        print(f"  Dimensions : {df.shape[0]} lignes, {df.shape[1]} colonnes")

        df_profil = profiler_dataframe(df)

        # --- Affichage résumé dans la console ---
        print("\n  Aperçu du profil :")
        print(df_profil.to_string(index=False))

        # --- Sauvegarde du profil détaillé ---
        chemin_profil = DOSSIER_PROFILS / f"profil_{nom_dataset}.csv"
        df_profil.to_csv(chemin_profil, sep=";", index=False, encoding="utf-8")
        print(f"\n  Profil sauvegardé : {chemin_profil}")

        resume_global.append({
            "dataset": nom_dataset,
            "nb_lignes": df.shape[0],
            "nb_colonnes": df.shape[1],
            "colonnes_avec_manquants": int((df_profil["nb_manquants"] > 0).sum()),
            "colonnes_100pct_uniques": int((df_profil["nb_uniques"] == df.shape[0]).sum()),
        })

    # Résumé global de tous les datasets
    if resume_global:

        print("\n" + "=" * 80)
        print("RÉSUMÉ GLOBAL")
        print("=" * 80)

        df_resume = pd.DataFrame(resume_global)
        print(df_resume.to_string(index=False))

        chemin_resume = DOSSIER_PROFILS / "resume_profils.csv"
        df_resume.to_csv(chemin_resume, sep=";", index=False, encoding="utf-8")
        print(f"\n Résumé global sauvegardé : {chemin_resume}")

    print("\n TÂCHE 42 TERMINÉE AVEC SUCCÈS.")


if __name__ == "__main__":
    realiser_profil_statistique()