"""
===============================================================================
PROJET : Mobilité et Sécurité Routière à Paris
MODULE : Tâche 36 — Création de la Base SQLite (Star Schema)
===============================================================================
"""

import sqlite3
import json
from pathlib import Path
import pandas as pd

# -----------------------------------------------------------------------------
# 1. DÉFINITION DES CHEMINS
# -----------------------------------------------------------------------------
DOSSIER_SCRIPT = Path(__file__).resolve().parent
RACINE_PROJET = (
    DOSSIER_SCRIPT.parent if DOSSIER_SCRIPT.name == "src" else DOSSIER_SCRIPT
)
DOSSIER_CURATED = RACINE_PROJET / "data" / "curated"
CHEMIN_DB = RACINE_PROJET / "data" / "mobilite_paris.db"


def lire_csv_adaptatif(chemin_relatif: str) -> pd.DataFrame:
    nom_fichier = Path(chemin_relatif).name
    chemins_possibles = [
        DOSSIER_CURATED / chemin_relatif,
        DOSSIER_CURATED / nom_fichier,
    ]
    chemin_final = next((p for p in chemins_possibles if p.exists()), None)
    if not chemin_final:
        print(f"[ATTENTION] Fichier introuvable : {nom_fichier}")
        return pd.DataFrame()
    for enc in ["utf-8-sig", "utf-8", "latin1"]:
        try:
            with open(chemin_final, "r", encoding=enc) as f:
                premiere_ligne = f.readline()
                separateur = ";" if ";" in premiere_ligne else ","
            return pd.read_csv(
                chemin_final, sep=separateur, encoding=enc, low_memory=False
            )
        except UnicodeDecodeError:
            continue
    return pd.DataFrame()


def extraire_geo_depuis_json(val):
    """Extrait 'lat_lon' depuis un JSON type {'lon': ..., 'lat': ...}"""
    try:
        if pd.isna(val):
            return None
        d = json.loads(val) if isinstance(val, str) else val
        if isinstance(d, dict) and "lat" in d and "lon" in d:
            return f"{round(float(d['lat']), 4)}_{round(float(d['lon']), 4)}"
    except Exception:
        pass
    return None


def creer_base_sqlite():
    print("=" * 80)
    print(f"[INFO] Initialisation de la base SQLite : {CHEMIN_DB.resolve()}")
    print("=" * 80)

    CHEMIN_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CHEMIN_DB)

    # -------------------------------------------------------------------------
    # 2. CHARGEMENT DES FICHIERS CURATED
    # -------------------------------------------------------------------------
    print("\n[1/4] Chargement des fichiers nettoyés depuis data/curated/...")

    df_caract = lire_csv_adaptatif("baac/caracteristiques_paris_2024_cles.csv")
    if df_caract.empty:
        df_caract = lire_csv_adaptatif("baac/caracteristiques_paris_clean.csv")

    df_usagers = lire_csv_adaptatif("baac/usagers_paris_2024_cles.csv")
    if df_usagers.empty:
        df_usagers = lire_csv_adaptatif("baac/usagers_paris_clean.csv")

    df_vehicules = lire_csv_adaptatif("baac/vehicules_paris_2024_cles.csv")
    if df_vehicules.empty:
        df_vehicules = lire_csv_adaptatif("baac/vehicules_paris_clean.csv")

    df_meteo = lire_csv_adaptatif("meteo_nettoye_cles.csv")
    if df_meteo.empty:
        df_meteo = lire_csv_adaptatif("meteo/meteo_paris_reference_daily.csv")

    df_pop = lire_csv_adaptatif("population_paris_nettoye_cles.csv")
    if df_pop.empty:
        df_pop = lire_csv_adaptatif("population/population_paris_2023.csv")

    df_ref_geo = lire_csv_adaptatif("referentiel_geo_nettoye_cles.csv")
    if df_ref_geo.empty:
        df_ref_geo = lire_csv_adaptatif("referentiel_geo_paris_clean.csv")

    df_trafic = lire_csv_adaptatif("trafic_nettoye_cles.csv")
    if df_trafic.empty:
        df_trafic = lire_csv_adaptatif(
            "trafic/trafic_2020_2024_agrege_semaine_clean.csv"
        )

    if df_caract.empty or df_usagers.empty:
        raise FileNotFoundError(
            "[ERREUR CRITIQUE] Caractéristiques ou Usagers introuvables."
        )

    # -------------------------------------------------------------------------
    # 2.1 HARMONISATION
    # -------------------------------------------------------------------------
    for df in [df_caract, df_usagers, df_vehicules]:
        if not df.empty:
            renames = {}
            for col in df.columns:
                if col.lower() == "num_acc":
                    renames[col] = "Num_Acc"
                elif col.lower() == "num_veh":
                    renames[col] = "num_veh"
                elif col.lower() == "com":
                    renames[col] = "com"
            df.rename(columns=renames, inplace=True)

    # -------------------------------------------------------------------------
    # 2.1bis CORRECTIF : normalisation du code commune INSEE ('com')
    # Colonne standard du fichier BAAC caracteristiques. Sert de clé fiable
    # pour la jointure population (contrairement à GEO qui est une clé
    # spatiale lat_lon). Normalisée en TEXT zéro-paddé sur 5 chiffres pour
    # matcher le format INSEE (ex: 75101 -> '75101').
    # -------------------------------------------------------------------------
    if "com" in df_caract.columns:
        com_num = pd.to_numeric(df_caract["com"], errors="coerce")
        df_caract["com"] = com_num.apply(
            lambda x: str(int(x)).zfill(5) if pd.notna(x) else None
        )
        print(f"  [DEBUG] com (code commune INSEE) : {df_caract['com'].notna().sum()} / {len(df_caract)}")
    else:
        df_caract["com"] = None
        print("  [ATTENTION] Colonne 'com' absente de caracteristiques : jointure population par com impossible.")

    # ✅ Dérivation GEO dans df_caract (virgule → point)
    if "lat" in df_caract.columns and "long" in df_caract.columns:
        lat_str = df_caract["lat"].astype(str).str.replace(",", ".", regex=False)
        lon_str = df_caract["long"].astype(str).str.replace(",", ".", regex=False)
        lat_r = pd.to_numeric(lat_str, errors="coerce").round(4)
        lon_r = pd.to_numeric(lon_str, errors="coerce").round(4)
        df_caract["lat"] = lat_r
        df_caract["lon"] = lon_r
        df_caract["GEO"] = (lat_r.astype(str) + "_" + lon_r.astype(str)).where(
            lat_r.notna() & lon_r.notna()
        )
        print(f"  [DEBUG] GEO accidents : {df_caract['GEO'].notna().sum()} / {len(df_caract)}")

    # Dérivation AAAAMMJJ
    for df in [df_caract, df_meteo, df_trafic]:
        if not df.empty and "AAAAMMJJ" not in df.columns and "date" in df.columns:
            df["AAAAMMJJ"] = pd.to_datetime(
                df["date"], errors="coerce"
            ).dt.strftime("%Y%m%d")

    # -------------------------------------------------------------------------
    # 3. CRÉATION DES DIMENSIONS
    # -------------------------------------------------------------------------
    print("\n[2/4] Génération des tables de dimensions...")

    # --- A. DIM_DATE ---
    if "AAAAMMJJ" in df_caract.columns:
        df_date_source = df_caract["AAAAMMJJ"].dropna().unique()
        dates_dt = pd.to_datetime(df_date_source, format="%Y%m%d", errors="coerce")
        iso = dates_dt.isocalendar()
        annee_semaine = (
            iso["year"].astype(str) + "-" + iso["week"].astype(str).str.zfill(2)
        )
        df_dim_date = pd.DataFrame({
            "AAAAMMJJ": df_date_source,
            "date": dates_dt.strftime("%Y-%m-%d"),
            "annee": dates_dt.year,
            "mois": dates_dt.month,
            "jour": dates_dt.day,
            "jour_semaine": dates_dt.day_name(),
            "is_weekend": dates_dt.dayofweek >= 5,
            "annee_semaine": annee_semaine,
        }).drop_duplicates(subset=["AAAAMMJJ"])
        df_dim_date.to_sql("DIM_DATE", conn, if_exists="replace", index=False)
        print(f"  [OK] DIM_DATE (8 colonnes, {len(df_dim_date)} lignes)")

    # --- B. DIM_GEO ---
    if "GEO" in df_caract.columns:
        df_geo_src = df_caract.copy()
        cols_geo = ["GEO", "lat", "lon"]
        if "arrondissement" in df_geo_src.columns:
            cols_geo.append("arrondissement")
        else:
            df_geo_src["arrondissement"] = None
            cols_geo.append("arrondissement")
        df_dim_geo = (
            df_geo_src[cols_geo]
            .dropna(subset=["GEO"])
            .drop_duplicates(subset=["GEO"])
        )
        df_dim_geo.to_sql("DIM_GEO", conn, if_exists="replace", index=False)
        print(f"  [OK] DIM_GEO (4 colonnes, {len(df_dim_geo)} lignes)")

    # --- C. DIM_POPULATION ---
    # CORRECTIF : la colonne code commune INSEE (ex: 'geo') et les colonnes
    # valeur/période (ex: 'obs_value', 'time_period') sont repérées de façon
    # insensible à la casse, car le format de la source varie. On ne garde
    # que la période la plus récente et on déduplique sur 'com' pour éviter
    # de dupliquer des lignes lors de la jointure de la tâche 38 (un export
    # INSEE API contient souvent plusieurs mesures/années par commune).
    if not df_pop.empty:
        print(f"  [DEBUG] Colonnes population disponibles : {list(df_pop.columns)}")
        col_insee_candidats = ["com", "geo", "codgeo", "code_insee", "insee_com", "code_commune"]
        col_com = next((c for c in df_pop.columns if c.strip().lower() in col_insee_candidats), None)
        col_obs = next((c for c in df_pop.columns if c.strip().lower() == "obs_value"), None)
        col_periode = next((c for c in df_pop.columns if c.strip().lower() == "time_period"), None)
        col_mesure = next((c for c in df_pop.columns if c.strip().lower() == "popref_measure_lib"), None)

        renames = {}
        if col_com and col_com != "com":
            renames[col_com] = "com"
        if col_obs:
            renames[col_obs] = "OBS_VALUE"
        if col_periode:
            renames[col_periode] = "TIME_PERIOD"
        df_pop = df_pop.rename(columns=renames)

        if "com" in df_pop.columns:
            com_pop_num = pd.to_numeric(df_pop["com"], errors="coerce")
            df_pop["com"] = com_pop_num.apply(
                lambda x: str(int(x)).zfill(5) if pd.notna(x) else None
            )

        if col_mesure and df_pop[col_mesure].nunique() > 1:
            mesures_dispo = df_pop[col_mesure].unique().tolist()
            print(f"  [DEBUG] Plusieurs mesures population détectées : {mesures_dispo}")
            if "Population totale" in mesures_dispo:
                df_pop = df_pop[df_pop[col_mesure] == "Population totale"]
                print("  [INFO] Population : mesure retenue = 'Population totale'")
            else:
                print(f"  [ATTENTION] 'Population totale' absente ; mesure retenue au hasard "
                      f"parmi {mesures_dispo} après déduplication — à vérifier en tâche 39.")

        if "TIME_PERIOD" in df_pop.columns and not df_pop.empty:
            periode_max = df_pop["TIME_PERIOD"].max()
            print(f"  [INFO] Population : {df_pop['TIME_PERIOD'].nunique()} période(s) détectée(s), "
                  f"on retient la plus récente ({periode_max})")
            df_pop = df_pop[df_pop["TIME_PERIOD"] == periode_max]

        cols_pop = [c for c in ["com", "OBS_VALUE", "TIME_PERIOD"] if c in df_pop.columns]
        if cols_pop:
            df_dim_pop = df_pop[cols_pop].drop_duplicates(subset=["com"] if "com" in cols_pop else None)
            df_dim_pop.to_sql("DIM_POPULATION", conn, if_exists="replace", index=False)
            print(f"  [OK] DIM_POPULATION ({len(cols_pop)} colonnes, clé = com, {len(df_dim_pop)} lignes)")
        else:
            print(f"  [ATTENTION] DIM_POPULATION NON chargée — colonnes utiles absentes "
                  f"parmi : {list(df_pop.columns)}")

    # --- D. DIM_METEO ---
    if not df_meteo.empty:
        cols_meteo = [c for c in ["AAAAMMJJ", "RR", "TN", "TX", "TM"] if c in df_meteo.columns]
        if "AAAAMMJJ" in cols_meteo:
            df_meteo[cols_meteo].drop_duplicates(subset=["AAAAMMJJ"]).to_sql(
                "DIM_METEO", conn, if_exists="replace", index=False
            )
            print(f"  [OK] DIM_METEO ({len(cols_meteo)} colonnes)")

    # --- E. DIM_REFERENTIELGEO ---
    if not df_ref_geo.empty:
        if "geo_point_2d" in df_ref_geo.columns:
            df_ref_geo["GEO"] = df_ref_geo["geo_point_2d"].apply(extraire_geo_depuis_json)
            print(f"  [DEBUG] GEO référentiel (source geo_point_2d) : "
                  f"{df_ref_geo['GEO'].notna().sum()} / {len(df_ref_geo)}")
        else:
            if "lat" in df_ref_geo.columns and "lon" in df_ref_geo.columns:
                lat_r = pd.to_numeric(
                    df_ref_geo["lat"].astype(str).str.replace(",", ".", regex=False),
                    errors="coerce",
                ).round(4)
                lon_r = pd.to_numeric(
                    df_ref_geo["lon"].astype(str).str.replace(",", ".", regex=False),
                    errors="coerce",
                ).round(4)
                df_ref_geo["GEO"] = (
                    lat_r.astype(str) + "_" + lon_r.astype(str)
                ).where(lat_r.notna() & lon_r.notna())
                print(f"  [DEBUG] GEO référentiel (source lat/lon) : "
                      f"{df_ref_geo['GEO'].notna().sum()} / {len(df_ref_geo)}")
            else:
                df_ref_geo["GEO"] = None
                print("  [ATTENTION] Aucune source pour GEO dans DIM_REFERENTIELGEO !")

        for col_oblig in ["iu_ac", "GEO", "libelle"]:
            if col_oblig not in df_ref_geo.columns:
                df_ref_geo[col_oblig] = None

        df_ref_geo[["iu_ac", "GEO", "libelle"]].drop_duplicates().to_sql(
            "DIM_REFERENTIELGEO", conn, if_exists="replace", index=False
        )
        print(f"  [OK] DIM_REFERENTIELGEO (3 colonnes, {len(df_ref_geo)} lignes)")
        print(f"  [DEBUG] Exemple GEO référentiel : "
              f"{df_ref_geo['GEO'].dropna().head(3).tolist()}")

    # --- F. DIM_TRAFIC ---
    # CORRECTIF : la table gardait une ligne par (iu_ac, AAAAMMJJ), alors que
    # la jointure de la tâche 38 se fait sur (iu_ac, annee_semaine) seul.
    # Plusieurs jours dans la même semaine matchaient donc chacun une ligne
    # FAIT_ACCIDENT, dupliquant des accidents dans FAIT_ACCIDENT_ENRICHI.
    # On agrège désormais réellement au grain hebdomadaire avant chargement.
    if not df_trafic.empty:
        if "AAAAMMJJ" in df_trafic.columns:
            dt_trafic = pd.to_datetime(
                df_trafic["AAAAMMJJ"].astype(str), format="%Y%m%d", errors="coerce"
            )
            iso_t = dt_trafic.dt.isocalendar()
            df_trafic["annee_semaine"] = (
                iso_t["year"].astype(str) + "-" + iso_t["week"].astype(str).str.zfill(2)
            )
        colonnes_mesures_trafic = [c for c in ["q_total", "q_moyen", "k_moyen"] if c in df_trafic.columns]
        if "iu_ac" in df_trafic.columns and "annee_semaine" in df_trafic.columns and colonnes_mesures_trafic:
            df_dim_trafic = (
                df_trafic
                .groupby(["iu_ac", "annee_semaine"], as_index=False)[colonnes_mesures_trafic]
                .mean()
            )
            df_dim_trafic["grain_trafic"] = "hebdomadaire"
            print(f"  [INFO] DIM_TRAFIC agrégée au grain (iu_ac, annee_semaine) : "
                  f"{len(df_trafic)} lignes source -> {len(df_dim_trafic)} lignes hebdo")
            df_dim_trafic.to_sql("DIM_TRAFIC", conn, if_exists="replace", index=False)
            print(f"  [OK] DIM_TRAFIC ({len(df_dim_trafic.columns)} colonnes, {len(df_dim_trafic)} lignes)")
        else:
            print("  ⚠️ iu_ac/annee_semaine/mesures absents de trafic : DIM_TRAFIC non chargée.")

    # -------------------------------------------------------------------------
    # 3.bis CORRECTIF : Uniformiser iu_ac en TEXT partout
    # -------------------------------------------------------------------------
    print("\n[INFO] Uniformisation du type iu_ac en TEXT...")
    for table in ["DIM_REFERENTIELGEO", "DIM_TRAFIC"]:
        try:
            conn.execute(f"""
                UPDATE {table}
                SET iu_ac = CAST(CAST(iu_ac AS INTEGER) AS TEXT)
                WHERE iu_ac IS NOT NULL
            """)
            conn.commit()
            cur = conn.cursor()
            cur.execute(f"SELECT typeof(iu_ac), COUNT(*) FROM {table} GROUP BY typeof(iu_ac)")
            print(f"  [OK] {table}.iu_ac : {cur.fetchall()}")
        except Exception as e:
            print(f"  [ATTENTION] {table}.iu_ac : {e}")

    # -------------------------------------------------------------------------
    # 4. TABLE DE FAITS : FAIT_ACCIDENT
    # -------------------------------------------------------------------------
    print("\n[3/4] Construction de FAIT_ACCIDENT...")

    if "id_usager" not in df_usagers.columns:
        num_acc_str = df_usagers["Num_Acc"].astype(str).str.strip()
        num_v = (
            df_usagers["num_veh"].astype(str).str.replace(r"\xa0|\s|Â", "", regex=True).str.strip()
            if "num_veh" in df_usagers.columns else "0"
        )
        plc = (
            df_usagers["place"].astype(str).str.replace(r"\xa0|\s|Â", "", regex=True).str.strip()
            if "place" in df_usagers.columns else "0"
        )
        df_usagers["id_usager"] = num_acc_str + "_" + num_v + "_" + plc

    df_fait = df_usagers.merge(df_caract, on="Num_Acc", how="inner")

    if (
        not df_vehicules.empty
        and "num_veh" in df_usagers.columns
        and "num_veh" in df_vehicules.columns
    ):
        cols_v = [c for c in ["Num_Acc", "num_veh", "catv"] if c in df_vehicules.columns]
        df_fait = df_fait.merge(df_vehicules[cols_v], on=["Num_Acc", "num_veh"], how="left")

    df_fait.reset_index(drop=True, inplace=True)
    df_fait["id_fait"] = df_fait.index + 1

    colonnes_pdf_stricte = [
        "id_fait", "Num_Acc", "id_usager", "AAAAMMJJ", "GEO", "com", "iu_ac",
        "lum", "atm", "col", "catu", "grav", "secu1", "secu2", "secu3", "catv",
    ]
    for col in colonnes_pdf_stricte:
        if col not in df_fait.columns:
            df_fait[col] = None

    df_fait_final = df_fait[colonnes_pdf_stricte]
    df_fait_final.to_sql("FAIT_ACCIDENT", conn, if_exists="replace", index=False)
    print(f"  [OK] FAIT_ACCIDENT générée avec {len(df_fait_final)} lignes.")
    print(f"  [DEBUG] com renseigné dans FAIT_ACCIDENT : "
          f"{df_fait_final['com'].notna().sum()} / {len(df_fait_final)}")

    # -------------------------------------------------------------------------
    # 4.bis CORRECTIF : Injecter iu_ac dans FAIT_ACCIDENT
    #   - Étape 1 : matching exact sur GEO (4 décimales)
    #   - Étape 2 : matching par proximité GPS (2 décimales ≈ 1 km)
    #   - Étape 3 : uniformisation TEXT
    # -------------------------------------------------------------------------
    print("\n[INFO] Injection iu_ac — matching exact sur GEO...")
    try:
        conn.execute("""
            UPDATE FAIT_ACCIDENT
            SET iu_ac = (
                SELECT r.iu_ac
                FROM DIM_REFERENTIELGEO r
                WHERE r.GEO = FAIT_ACCIDENT.GEO
                  AND r.iu_ac IS NOT NULL
                LIMIT 1
            )
            WHERE iu_ac IS NULL
              AND EXISTS (
                  SELECT 1 FROM DIM_REFERENTIELGEO r
                  WHERE r.GEO = FAIT_ACCIDENT.GEO
                    AND r.iu_ac IS NOT NULL
              )
        """)
        conn.commit()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM FAIT_ACCIDENT WHERE iu_ac IS NOT NULL")
        n1 = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM FAIT_ACCIDENT")
        t = cur.fetchone()[0]
        print(f"  [OK] Après matching exact : {n1} / {t} ({100*n1/t:.1f}%)")
    except Exception as e:
        print(f"  [ATTENTION] Matching exact impossible : {e}")

    print("\n[INFO] Injection iu_ac — matching par proximité (grille ~1km, lat ET lon)...")
    try:
        conn.execute("""
            UPDATE FAIT_ACCIDENT
            SET iu_ac = (
                SELECT r.iu_ac
                FROM DIM_REFERENTIELGEO r
                WHERE round(CAST(substr(r.GEO, 1, instr(r.GEO, '_') - 1) AS REAL), 2)
                      = round(CAST(substr(FAIT_ACCIDENT.GEO, 1, instr(FAIT_ACCIDENT.GEO, '_') - 1) AS REAL), 2)
                  AND round(CAST(substr(r.GEO, instr(r.GEO, '_') + 1) AS REAL), 2)
                      = round(CAST(substr(FAIT_ACCIDENT.GEO, instr(FAIT_ACCIDENT.GEO, '_') + 1) AS REAL), 2)
                  AND r.iu_ac IS NOT NULL
                LIMIT 1
            )
            WHERE iu_ac IS NULL
              AND GEO IS NOT NULL
              AND EXISTS (
                  SELECT 1 FROM DIM_REFERENTIELGEO r
                  WHERE round(CAST(substr(r.GEO, 1, instr(r.GEO, '_') - 1) AS REAL), 2)
                        = round(CAST(substr(FAIT_ACCIDENT.GEO, 1, instr(FAIT_ACCIDENT.GEO, '_') - 1) AS REAL), 2)
                    AND round(CAST(substr(r.GEO, instr(r.GEO, '_') + 1) AS REAL), 2)
                        = round(CAST(substr(FAIT_ACCIDENT.GEO, instr(FAIT_ACCIDENT.GEO, '_') + 1) AS REAL), 2)
                    AND r.iu_ac IS NOT NULL
              )
        """)
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM FAIT_ACCIDENT WHERE iu_ac IS NOT NULL")
        n2 = cur.fetchone()[0]
        print(f"  [OK] Après matching proximité : {n2} / {t} ({100*n2/t:.1f}%)")
    except Exception as e:
        print(f"  [ATTENTION] Matching proximité impossible : {e}")

    print("\n[INFO] Uniformisation du type iu_ac dans FAIT_ACCIDENT en TEXT...")
    try:
        conn.execute("""
            UPDATE FAIT_ACCIDENT
            SET iu_ac = CAST(CAST(iu_ac AS INTEGER) AS TEXT)
            WHERE iu_ac IS NOT NULL
        """)
        conn.commit()
        cur = conn.cursor()
        cur.execute("SELECT typeof(iu_ac), COUNT(*) FROM FAIT_ACCIDENT GROUP BY typeof(iu_ac)")
        print(f"  [OK] FAIT_ACCIDENT.iu_ac : {cur.fetchall()}")
    except Exception as e:
        print(f"  [ATTENTION] Uniformisation impossible : {e}")

    # -------------------------------------------------------------------------
    # 5. VÉRIFICATION FINALE
    # -------------------------------------------------------------------------
    print("\n[4/4] Vérification finale...")
    tables = [
        "FAIT_ACCIDENT", "DIM_DATE", "DIM_GEO", "DIM_METEO",
        "DIM_TRAFIC", "DIM_POPULATION", "DIM_REFERENTIELGEO",
    ]
    print("-" * 50)
    for t in tables:
        try:
            count = pd.read_sql(f"SELECT COUNT(*) FROM {t}", conn).iloc[0, 0]
            print(f"  • {t:<20} : {count:>7} lignes")
        except Exception:
            print(f"  • {t:<20} : [NON CRÉÉE]")
    print("-" * 50)

    conn.close()
    print("\n" + "=" * 80)
    print(" [SUCCÈS] Base 'mobilite_paris.db' générée !")
    print("=" * 80)


if __name__ == "__main__":
    creer_base_sqlite()