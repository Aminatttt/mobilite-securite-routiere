# src/clean_baac.py
"""
clean_baac.py
-------------
Nettoyage automatique des données BAAC (2020-2024).
"""

import re
import unicodedata
from pathlib import Path
import pandas as pd
from utils_log import creer_logger

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
logger = creer_logger("clean_baac", SCRIPT_DIR)

RACINES_RAW_BAAC = (
    BASE_DIR / "data" / "raw" / "baac",
    SCRIPT_DIR / "data" / "raw" / "baac",
)


def trouver_dossier_raw_baac():
    dossiers = []
    for racine in RACINES_RAW_BAAC:
        if racine.exists():
            dossiers.extend(
                [
                    d
                    for d in racine.iterdir()
                    if d.is_dir() and any(d.glob("*.csv"))
                ]
            )
    if not dossiers:
        return RACINES_RAW_BAAC[0] / "2026-09-10"
    return max(dossiers, key=lambda d: d.name)


DOSSIER_RAW = trouver_dossier_raw_baac()
DOSSIER_CURATED = BASE_DIR / "data" / "curated" / "baac"
DOSSIER_CURATED.mkdir(parents=True, exist_ok=True)

DEPARTEMENT = "75"
SEPARATEUR = ";"
ENCODING = "latin1"

TYPES_BAAC = {
    "caracteristiques": [],
    "lieux": [],
    "usagers": [],
    "vehicules": [],
}
NUM_ACC_PARIS = set()


def normaliser_nom(texte):
    texte = str(texte).strip().lower()
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", texte)


def reconnaitre_type_fichier(nom_fichier):
    nom = normaliser_nom(nom_fichier)
    if "immatricule" in nom:
        return None
    if any(k in nom for k in ["caracteristique", "caracteristiques", "caract"]):
        return "caracteristiques"
    if "lieu" in nom:
        return "lieux"
    if "usager" in nom:
        return "usagers"
    if "vehicule" in nom:
        return "vehicules"
    return None


def extraire_annee(nom_fichier):
    res = re.search(r"(20\d{2})", nom_fichier)
    return res.group(1) if res else None


def nettoyer_noms_colonnes(df):
    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]
    return df


def nettoyer_valeurs(df):
    for col in df.columns:
        if df[col].dtype == "object" or isinstance(
            df[col].dtype, pd.StringDtype
        ):
            df[col] = df[col].astype("string").str.strip()
            df[col] = df[col].replace(
                {"": pd.NA, "nan": pd.NA, "None": pd.NA, "NULL": pd.NA, "-1": pd.NA}
            )
        elif pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].replace(-1, pd.NA)
    return df


def trouver_colonne(df, noms_possibles):
    cols_norm = {normaliser_nom(c): c for c in df.columns}
    for nom in noms_possibles:
        if normaliser_nom(nom) in cols_norm:
            return cols_norm[normaliser_nom(nom)]
    return None


def filtrer_paris(df, type_baac):
    col_dep = trouver_colonne(df, ["dep", "Departement", "departement"])
    if col_dep is None:
        col_num = trouver_colonne(df, ["Num_Acc", "num_acc", "NumAcc"])
        if NUM_ACC_PARIS and col_num:
            return df[
                df[col_num].astype("string").isin(NUM_ACC_PARIS)
            ].copy()
        return df

    dep_str = df[col_dep].astype("string").str.strip()
    return df[dep_str.isin([DEPARTEMENT, DEPARTEMENT.zfill(3)])].copy()


def normaliser_num_acc(df):
    col = trouver_colonne(df, ["Num_Acc", "num_acc", "NumAcc", "Accident_Id"])
    if col:
        if col != "Num_Acc":
            df = df.rename(columns={col: "Num_Acc"})
        df["Num_Acc"] = df["Num_Acc"].astype("string").str.strip()
    return df


def dedupliquer_lieux(df):
    if "Num_Acc" not in df.columns:
        return df
    l_avant = len(df)
    compte = df.groupby("Num_Acc").size().rename("nb_voies_intersection")
    df = df.merge(compte, on="Num_Acc", how="left")
    df["intersection"] = df["nb_voies_intersection"] > 1
    df = (
        df.sort_values("Num_Acc")
        .drop_duplicates(subset="Num_Acc", keep="first")
        .reset_index(drop=True)
    )
    logger.info(
        f"Lieux dedupliques : {l_avant:,} -> {len(df):,} ({int((compte > 1).sum()):,} intersections)"
    )
    return df


def nettoyer_fichier(chemin, type_baac, annee):
    try:
        df = pd.read_csv(
            chemin, sep=SEPARATEUR, encoding=ENCODING, low_memory=False
        )
    except Exception as e:
        logger.error(f"Erreur lecture {chemin.name}: {e}")
        return None, None

    l_avant = len(df)
    df = nettoyer_noms_colonnes(df).dropna(how="all")
    df = nettoyer_valeurs(df)
    df = normaliser_num_acc(df)
    df = filtrer_paris(df, type_baac)

    doublons = int(df.duplicated().sum())
    if doublons > 0:
        df = df.drop_duplicates()

    rapport = {
        "fichier": chemin.name,
        "type": type_baac,
        "annee": annee,
        "lignes_avant": l_avant,
        "lignes_apres": len(df),
        "doublons": doublons,
        "statut": "OK",
    }
    return df, rapport


def main():
    logger.info("=== DEBUT CLEAN BAAC ===")
    fichiers = sorted(DOSSIER_RAW.glob("*.csv"))
    for f in fichiers:
        t = reconnaitre_type_fichier(f.name)
        a = extraire_annee(f.name)
        if t:
            TYPES_BAAC[t].append((f, a))

    rapports = []
    for t_baac, liste in TYPES_BAAC.items():
        if not liste:
            continue
        dfs = []
        for chemin, annee in liste:
            df, rap = nettoyer_fichier(chemin, t_baac, annee)
            if rap:
                rapports.append(rap)
            if df is not None:
                if annee:
                    df["annee_source"] = int(annee)
                dfs.append(df)

        if dfs:
            df_final = pd.concat(dfs, ignore_index=True, sort=False)
            if t_baac == "caracteristiques":
                NUM_ACC_PARIS.clear()
                NUM_ACC_PARIS.update(
                    df_final["Num_Acc"].dropna().astype("string").tolist()
                )
            if t_baac == "lieux":
                df_final = dedupliquer_lieux(df_final)

            out_file = DOSSIER_CURATED / f"{t_baac}_paris_clean.csv"
            df_final.to_csv(out_file, sep=";", index=False, encoding="utf-8-sig")
            logger.info(f"Fichier genere : {out_file} ({len(df_final):,} lignes)")

    if rapports:
        pd.DataFrame(rapports).to_csv(
            DOSSIER_CURATED / "rapport_qualite_baac.csv",
            sep=";",
            index=False,
            encoding="utf-8-sig",
        )
    logger.info("=== FIN CLEAN BAAC ===")


if __name__ == "__main__":
    main()