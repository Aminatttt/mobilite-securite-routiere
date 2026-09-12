"""
HARMONISATION DES DATES (TACHE 27)
----------------------------------
- Recherche dynamique de la racine du projet (adaptable a chaque utilisateur).
- Traite uniquement les fichiers CSV de data/curated/ ayant des champs temporels bruts.
- Ignore les tables sans date propre (lieux, usagers, vehicules) : leur date viendra par jointure num_acc en Phase 3.
- Ecrase directement le fichier source (pas de doublons _harmonise.csv).
- Idempotent : saute les fichiers qui possedent deja la colonne 'date'.

CORRECTION : ajout de la reconnaissance des colonnes 't_debut'/'t_fin' produites
par la version corrigee du script trafic (qui n'a plus de colonne 't_1h').
"""

from pathlib import Path
import pandas as pd


def trouver_racine_projet(depart: Path) -> Path:
    dossier = depart.resolve()

    while dossier.name.lower() in ["curated", "raw", "data", "src"]:
        dossier = dossier.parent

    curr = dossier
    while curr != curr.parent:
        if (curr / "data").exists() and (curr / "data").is_dir():
            return curr
        curr = curr.parent

    return depart.resolve().parent


DOSSIER_SCRIPT = Path(__file__).resolve().parent
RACINE_PROJET = trouver_racine_projet(DOSSIER_SCRIPT)
CURATED_DIR = RACINE_PROJET / "data" / "curated"

COLONNES_TEMPORELLES = {
    "an", "mois", "jour", "aaaammjj", "t_1h", "t_debut",
    "time_period", "année", "annee",
}


def lire_csv(path):
    for sep in [";", ",", "\t"]:
        try:
            df = pd.read_csv(path, sep=sep, low_memory=False, encoding="utf-8-sig")
            if len(df.columns) > 1:
                return df
        except Exception:
            continue

    for sep in [";", ",", "\t"]:
        try:
            df = pd.read_csv(path, sep=sep, low_memory=False, encoding="latin-1")
            if len(df.columns) > 1:
                return df
        except Exception:
            continue

    return pd.read_csv(path, sep=None, engine="python")


def construire_colonne_date(df):
    cols_a_supprimer = []

    if {"an", "mois", "jour"}.issubset(set(df.columns)):
        annee = df["an"].apply(lambda x: f"20{int(x):02d}" if str(x).isdigit() and int(x) < 100 else str(x))
        mois = df["mois"].astype(str).str.zfill(2)
        jour = df["jour"].astype(str).str.zfill(2)
        heure = df["hrmn"].astype(str).str.replace(":", "").str.zfill(4) if "hrmn" in df.columns else "0000"
        heure_fmt = heure.str[:2] + ":" + heure.str[2:] + ":00"

        df["date"] = pd.to_datetime(annee + "-" + mois + "-" + jour + " " + heure_fmt, errors="coerce")
        cols_a_supprimer.extend(["an", "mois", "jour", "hrmn"])

    elif "aaaammjj" in df.columns:
        df["date"] = pd.to_datetime(df["aaaammjj"].astype(str), format="%Y%m%d", errors="coerce")
        cols_a_supprimer.append("aaaammjj")

    elif "t_1h" in df.columns:
        df["date"] = pd.to_datetime(df["t_1h"], errors="coerce")

    # NOUVEAU : trafic corrige, une ligne = une semaine agregee par capteur
    # on prend t_debut comme date de reference de la semaine
    elif "t_debut" in df.columns:
        df["date"] = pd.to_datetime(df["t_debut"], errors="coerce")

    elif "time_period" in df.columns:
        df["date"] = pd.to_datetime(df["time_period"].astype(str) + "-01-01", errors="coerce")

    elif "année" in df.columns or "annee" in df.columns:
        col_a = "année" if "année" in df.columns else "annee"
        df["date"] = pd.to_datetime(df[col_a].astype(str) + "-01-01", errors="coerce")

    if cols_a_supprimer:
        df.drop(columns=cols_a_supprimer, errors="ignore", inplace=True)

    return df


def harmoniser_dates():
    print("--- HARMONISATION DES DATES (TACHE 27) ---")
    print(f"[INFO] Racine du projet detectee : {RACINE_PROJET}")
    print(f"[INFO] Dossier curated cible : {CURATED_DIR}")

    if not CURATED_DIR.exists():
        print(f"[ERREUR] Le dossier {CURATED_DIR} n'existe pas.")
        return

    fichiers_curated = list(CURATED_DIR.rglob("*.csv"))
    if not fichiers_curated:
        print(f"[ERREUR] Aucun fichier CSV dans {CURATED_DIR}.")
        return

    print(f"[INFO] {len(fichiers_curated)} fichier(s) detecte(s).")

    for file_path in fichiers_curated:
        df = lire_csv(file_path)
        df.columns = df.columns.str.lower().str.strip()

        if "date" in df.columns:
            print(f"  [SKIP] Colonne 'date' deja existante : {file_path.name}")
            continue

        if not any(col in df.columns for col in COLONNES_TEMPORELLES):
            print(f"  [SKIP] Pas concerne (date viendra par jointure Phase 3) : {file_path.name}")
            continue

        df = construire_colonne_date(df)
        if "date" not in df.columns:
            continue

        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d %H:%M:%S")

        cols = [c for c in df.columns if c != "date"]
        cols.insert(1, "date")
        df = df[cols]

        df.to_csv(file_path, sep=";", index=False, encoding="utf-8")
        print(f"  [OK] Date harmonisee : {file_path.name}")


if __name__ == "__main__":
    harmoniser_dates()